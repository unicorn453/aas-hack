"""Transform complete company XLSX extraction into clean AAS JSON from references."""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

from excel_to_aasx.company_config import DEFAULT_COMPANY_CONFIG, load_company_config, sheet_templates
from excel_to_aasx.logging import classified, generated, warning

PLACEHOLDER_VALUES = {"", "#", "-", "n/a", "N/A", "not specified", "Not specified"}
OPTIONAL_CARDINALITIES = {"ZeroToOne", "ZeroToMany"}
DEFAULT_GENERATION_POLICY = {
    "emptyActualValue": "skip",
    "mandatoryMissingValue": "dummy",
    "optionalEmptyTemplateBranches": "prune",
    "reviewFiles": "always",
    "logLevel": "normal",
}
GENERIC_ARBITRARY_SEMANTIC = "https://admin-shell.io/SMT/General/Arbitrary"
TECHNICAL_ARBITRARY_PLACEHOLDERS = {
    "Section",
    "ArbitrarySMC",
    "ArbitrarySML",
    "ArbitraryProperty",
    "ArbitraryMLP",
    "ArbitraryRange",
}
LANGUAGE_STRING_FIELDS = {
    "description",
    "displayName",
    "preferredName",
    "shortName",
    "definition",
}


@dataclass(frozen=True)
class InputRow:
    sheet: str
    row: int
    id_short: str
    field_type: str
    semantic_id: str
    actual_value: str
    section_path: tuple[str, ...]


@dataclass
class Candidate:
    element: dict[str, Any]
    path: str
    id_short: str
    semantic_id: str
    model_type: str
    value_type: str


@dataclass(frozen=True)
class TemplateEntry:
    path: str
    id_short: str
    semantic_id: str
    model_type: str
    value_type: str
    cardinality: str
    is_arbitrary_placeholder: bool


@dataclass(frozen=True)
class RowClassification:
    row: InputRow
    classification: str
    reason: str
    template_path: str
    final_path: str


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return normalized or "item"


def aas_idshort(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    if not normalized:
        normalized = fallback
    if not re.match(r"[A-Za-z]", normalized):
        normalized = f"Value_{normalized}"
    return normalized[:128]


def semantic_id(element: dict[str, Any]) -> str:
    keys = (element.get("semanticId") or {}).get("keys") or []
    return text(keys[-1].get("value")) if keys else ""


def cardinality(element: dict[str, Any]) -> str:
    for qualifier in element.get("qualifiers", []) or []:
        if isinstance(qualifier, dict) and qualifier.get("type") == "SMT/Cardinality":
            return text(qualifier.get("value"))
    return ""


def normalized_semantic(value: str) -> str:
    return text(value).replace("https://api.eclass-cdp.com/", "").lower()


def children(element: dict[str, Any]) -> list[dict[str, Any]]:
    value = element.get("value")
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    submodel_elements = element.get("submodelElements")
    if isinstance(submodel_elements, list):
        return submodel_elements
    return []


def template_path_name(element: dict[str, Any], parent_model_type: str = "") -> str:
    id_short = "[]" if parent_model_type == "SubmodelElementList" else text(element.get("idShort")) or "[]"
    return id_short


def template_index(
    element: dict[str, Any],
    parent_path: str = "",
    parent_model_type: str = "",
) -> list[TemplateEntry]:
    path_part = template_path_name(element, parent_model_type)
    path = f"{parent_path}/{path_part}" if parent_path else path_part
    id_short = text(element.get("idShort"))
    semantic = semantic_id(element)
    model_type = text(element.get("modelType"))
    entries = [
        TemplateEntry(
            path=path,
            id_short=id_short,
            semantic_id=semantic,
            model_type=model_type,
            value_type=text(element.get("valueType")),
            cardinality=cardinality(element),
            is_arbitrary_placeholder=(
                normalized_semantic(semantic) == normalized_semantic(GENERIC_ARBITRARY_SEMANTIC)
                and id_short in TECHNICAL_ARBITRARY_PLACEHOLDERS
            ),
        )
    ]
    for child in children(element):
        entries.extend(template_index(child, path, model_type))
    return entries


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    generated(path)


def load_rows(sheet_json: dict[str, Any]) -> list[InputRow]:
    rows: list[InputRow] = []
    for item in sheet_json.get("parsedRows", []):
        rows.append(
            InputRow(
                sheet=sheet_json["sheet"],
                row=int(item["row"]),
                id_short=text(item.get("idShort")),
                field_type=text(item.get("fieldType")),
                semantic_id=text(item.get("semanticId")),
                actual_value=text(item.get("actualValue")),
                section_path=tuple(text(part) for part in item.get("sectionPath", [])),
            )
        )
    return rows


def meaningful_row(row: InputRow) -> bool:
    if row.actual_value in PLACEHOLDER_VALUES:
        return False
    lowered = row.actual_value.lower()
    if lowered.startswith("see section") or lowered.startswith("list containing"):
        return False
    if row.id_short.endswith(":"):
        return False
    return True


def has_actual_value(row: InputRow) -> bool:
    return row.actual_value not in PLACEHOLDER_VALUES


def generation_policy(config: dict[str, Any]) -> dict[str, str]:
    policy = {**DEFAULT_GENERATION_POLICY, **config.get("generationPolicy", {})}
    allowed_values = {
        "emptyActualValue": {"skip", "preserve-empty", "dummy"},
        "mandatoryMissingValue": {"error", "dummy", "preserve-empty"},
        "optionalEmptyTemplateBranches": {"prune", "keep-empty", "dummy"},
        "reviewFiles": {"always", "issues-only", "off"},
        "logLevel": {"quiet", "normal", "detailed"},
    }
    for key, allowed in allowed_values.items():
        if policy[key] not in allowed:
            raise ValueError(
                f"Invalid generationPolicy.{key}={policy[key]!r}; "
                f"expected one of {sorted(allowed)}"
            )
    return policy


def row_has_mappable_empty_value(row: InputRow, policy: dict[str, str]) -> bool:
    if has_actual_value(row):
        return False
    if policy["emptyActualValue"] not in {"preserve-empty", "dummy"}:
        return False
    if is_template_scaffold_row(row):
        return False
    if row.id_short.endswith(":"):
        return False
    lowered = row.actual_value.lower()
    return not (lowered.startswith("see section") or lowered.startswith("list containing"))


def row_can_enter_mapping(row: InputRow, policy: dict[str, str]) -> bool:
    return meaningful_row(row) or row_has_mappable_empty_value(row, policy)


def value_for(rows: list[InputRow], *id_shorts: str) -> str:
    wanted = set(id_shorts)
    for row in rows:
        if row.id_short in wanted and meaningful_row(row):
            return strip_language_suffix(row.actual_value)
    return ""


def thumbnail_for(rows: list[InputRow]) -> dict[str, str] | None:
    path = ""
    for id_short in ("ImageFile", "CompanyLogo"):
        path = value_for(rows, id_short)
        if path:
            break
    if not path:
        return None
    content_type = infer_content_type(path)
    if not content_type.startswith("image/"):
        return None
    return {"path": path, "contentType": content_type}


def strip_language_suffix(value: str) -> str:
    match = re.match(r"^(.*)@([a-z]{2})$", value, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1) if match else value


def split_lang(value: str) -> tuple[str, str]:
    match = re.match(r"^(.*)@([a-z]{2})$", value, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1), match.group(2).lower()
    return value, "en"


def clear_values(element: dict[str, Any]) -> None:
    for child in children(element):
        clear_values(child)
    model_type = element.get("modelType")
    if model_type in {"Property", "Range", "File", "Blob", "ReferenceElement"}:
        element.pop("value", None)
    elif model_type == "MultiLanguageProperty":
        element.pop("value", None)


def remove_empty_idshorts(element: Any) -> None:
    if isinstance(element, dict):
        if element.get("idShort") == "":
            element.pop("idShort", None)
        for value in element.values():
            remove_empty_idshorts(value)
    elif isinstance(element, list):
        for item in element:
            remove_empty_idshorts(item)


def deduplicate_language_strings(field: str, values: Any) -> Any:
    if not isinstance(values, list):
        return values

    merged: dict[str, dict[str, str]] = {}
    ordered_languages: list[str] = []
    for item in values:
        if not isinstance(item, dict) or "language" not in item:
            return values
        language = text(item.get("language")) or "en"
        item_text = text(item.get("text"))
        if language not in merged:
            merged[language] = {**item, "language": language}
            ordered_languages.append(language)
            continue
        if field == "shortName":
            continue
        existing_text = text(merged[language].get("text"))
        if item_text and item_text not in existing_text:
            merged[language]["text"] = (
                f"{existing_text}\n{item_text}" if existing_text else item_text
            )

    result = [merged[language] for language in ordered_languages]
    if field == "shortName":
        result = [item for item in result if len(text(item.get("text"))) <= 18]
    return result


def remove_template_qualifiers(element: dict[str, Any]) -> None:
    qualifiers = element.get("qualifiers")
    if not isinstance(qualifiers, list):
        return

    kept = []
    seen_types: set[str] = set()
    for qualifier in qualifiers:
        if not isinstance(qualifier, dict):
            kept.append(qualifier)
            continue
        if qualifier.get("kind") == "TemplateQualifier":
            continue
        qualifier_type = text(qualifier.get("type"))
        if qualifier_type and qualifier_type in seen_types:
            continue
        if qualifier_type:
            seen_types.add(qualifier_type)
        kept.append(qualifier)

    if kept:
        element["qualifiers"] = kept
    else:
        element.pop("qualifiers", None)


def deduplicate_child_idshorts(element: dict[str, Any]) -> None:
    for field in ("submodelElements", "value"):
        children_value = element.get(field)
        if not isinstance(children_value, list):
            continue
        seen: dict[str, int] = {}
        for child in children_value:
            if not isinstance(child, dict):
                continue
            id_short = text(child.get("idShort"))
            if not id_short:
                continue
            count = seen.get(id_short, 0) + 1
            seen[id_short] = count
            if count == 1:
                continue
            child["idShort"] = aas_idshort(f"{id_short}_{count}", "Value")


def normalize_instance_payload(payload: Any, parent_model_type: str = "") -> None:
    if isinstance(payload, dict):
        if parent_model_type == "SubmodelElementList":
            payload.pop("idShort", None)

        for field in LANGUAGE_STRING_FIELDS:
            if field in payload:
                payload[field] = deduplicate_language_strings(field, payload[field])
                if payload[field] == []:
                    payload.pop(field)

        remove_template_qualifiers(payload)
        deduplicate_child_idshorts(payload)

        model_type = text(payload.get("modelType"))
        for value in payload.values():
            normalize_instance_payload(value, model_type)
    elif isinstance(payload, list):
        for item in payload:
            normalize_instance_payload(item, parent_model_type)


def candidate_elements(element: dict[str, Any], parent_path: str = "") -> list[Candidate]:
    id_short = text(element.get("idShort"))
    path = f"{parent_path}/{id_short or '[]'}" if parent_path else id_short or "[]"
    result: list[Candidate] = []

    model_type = text(element.get("modelType"))
    if model_type in {"Property", "MultiLanguageProperty", "File", "Range"}:
        result.append(
            Candidate(
                element=element,
                path=path,
                id_short=id_short,
                semantic_id=semantic_id(element),
                model_type=model_type,
                value_type=text(element.get("valueType")),
            )
        )

    if model_type == "SubmodelElementList":
        list_children = children(element)
        if len(list_children) == 1:
            child = list_children[0]
            child_model = text(child.get("modelType"))
            if child_model in {"Property", "MultiLanguageProperty", "File", "Range"}:
                result.append(
                    Candidate(
                        element=child,
                        path=f"{path}/[]",
                        id_short=text(child.get("idShort")) or id_short,
                        semantic_id=semantic_id(child) or semantic_id(element),
                        model_type=child_model,
                        value_type=text(child.get("valueType")),
                    )
                )

    for child in children(element):
        result.extend(candidate_elements(child, path))
    return result


def score(row: InputRow, candidate: Candidate) -> int:
    row_sem = normalized_semantic(row.semantic_id)
    candidate_sem = normalized_semantic(candidate.semantic_id)
    value = 0
    if row.id_short and row.id_short == candidate.id_short:
        value += 40
    if row_sem and candidate_sem and row_sem == candidate_sem:
        value += 45
    if row_sem and candidate_sem and (row_sem in candidate_sem or candidate_sem in row_sem):
        value += 10
    if row.id_short and row.id_short.lower() in candidate.path.lower():
        value += 8
    if expected_model_type(row.field_type) == candidate.model_type:
        value += 4
    return value


def expected_model_type(field_type: str) -> str:
    lowered = field_type.lower()
    if "submodelelementcollection" in lowered:
        return "SubmodelElementCollection"
    if "submodelelementlist" in lowered:
        return "SubmodelElementList"
    if "multilanguage" in lowered or "langstring" in lowered:
        return "MultiLanguageProperty"
    if "file" in lowered:
        return "File"
    if "range" in lowered:
        return "Range"
    if "property" in lowered or "string" in lowered or "decimal" in lowered or "double" in lowered:
        return "Property"
    if "boolean" in lowered or "integer" in lowered or "date" in lowered or "anyuri" in lowered:
        return "Property"
    return ""


def best_candidate(
    row: InputRow,
    candidates: list[Candidate],
    used_paths: set[str],
) -> tuple[Candidate | None, int]:
    best: Candidate | None = None
    best_score = 0
    for candidate in candidates:
        if candidate.path in used_paths:
            continue
        candidate_score = score(row, candidate)
        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score
    if best_score < 20:
        return None, best_score
    return best, best_score


def fill_element(
    element: dict[str, Any],
    row: InputRow,
    policy: dict[str, str] | None = None,
) -> None:
    policy = policy or DEFAULT_GENERATION_POLICY
    model_type = element.get("modelType")
    if not has_actual_value(row):
        if policy["emptyActualValue"] == "dummy":
            fill_dummy_value(element)
            return
        if policy["emptyActualValue"] == "preserve-empty":
            add_missing_value_status(element)
    if model_type == "MultiLanguageProperty":
        text_value, language = split_lang(row.actual_value)
        element["value"] = [{"language": language, "text": text_value}]
    elif model_type == "File":
        element["value"] = normalize_uri_value(row.actual_value)
        element["contentType"] = infer_content_type(element["value"])
    elif model_type == "Property":
        element["value"] = normalize_value(row.actual_value, text(element.get("valueType")) or infer_value_type(row.field_type))
    elif model_type == "Range":
        element["min"] = row.actual_value
        element["max"] = row.actual_value


def infer_value_type(field_type: str) -> str:
    lowered = field_type.lower()
    if "boolean" in lowered:
        return "xs:boolean"
    if "datetime" in lowered:
        return "xs:dateTime"
    if re.search(r"\bdate\b", lowered):
        return "xs:date"
    if "decimal" in lowered:
        return "xs:decimal"
    if "double" in lowered:
        return "xs:double"
    if "integer" in lowered or "int" in lowered:
        return "xs:integer"
    if "uri" in lowered:
        return "xs:anyURI"
    return "xs:string"


def normalize_value(value: str, value_type: str) -> str:
    if value_type == "xs:boolean":
        return value.lower()
    if value_type == "xs:date":
        return normalize_date(value)
    if value_type == "xs:dateTime":
        return normalize_datetime(value)
    if value_type == "xs:anyURI":
        return normalize_uri_value(value)
    return value


def normalize_uri_value(value: str) -> str:
    normalized = re.sub(r"^\s*\[DUMMY\]\s*", "", value).strip()
    if not normalized:
        return normalized
    parts = urlsplit(normalized)
    if parts.scheme:
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                quote(parts.path, safe="/%:@"),
                quote(parts.query, safe="=&?/%:@"),
                quote(parts.fragment, safe="=&?/%:@"),
            )
        )
    return quote(normalized, safe="/%:@;,.()_-")


def normalize_date(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00(?:\+00:00)?", value):
        return value[:10]
    if re.fullmatch(r"\d+(\.0)?", value):
        serial = int(float(value))
        base = datetime.date(1899, 12, 30)
        return (base + datetime.timedelta(days=serial)).isoformat()
    return value


def normalize_datetime(value: str) -> str:
    if re.fullmatch(r"\d+(\.0)?", value):
        return f"{normalize_date(value)}T00:00:00"
    return value


def infer_content_type(value: str) -> str:
    lowered = value.lower()
    if lowered.endswith(".pdf"):
        return "application/pdf"
    if ".png" in lowered:
        return "image/png"
    if ".jpg" in lowered or ".jpeg" in lowered:
        return "image/jpeg"
    if ".webp" in lowered or "fwebp" in lowered:
        return "image/webp"
    return "application/octet-stream"


def fill_standard_matches(
    submodel: dict[str, Any],
    rows: list[InputRow],
    policy: dict[str, str],
) -> tuple[list[dict[str, Any]], list[InputRow]]:
    candidates = candidate_elements(submodel)
    used_paths: set[str] = set()
    matched: list[dict[str, Any]] = []
    unmatched: list[InputRow] = []

    for row in rows:
        if not row_can_enter_mapping(row, policy):
            continue
        if is_technical_arbitrary_row(row):
            unmatched.append(row)
            continue
        candidate, match_score = best_candidate(row, candidates, used_paths)
        if candidate is None:
            unmatched.append(row)
            continue
        fill_element(candidate.element, row, policy)
        used_paths.add(candidate.path)
        matched.append(match_record(row, candidate, match_score, "standard"))

    return matched, unmatched


def is_technical_arbitrary_row(row: InputRow) -> bool:
    return normalized_semantic(row.semantic_id) == normalized_semantic(GENERIC_ARBITRARY_SEMANTIC)


def is_template_scaffold_row(row: InputRow) -> bool:
    if row.id_short in TECHNICAL_ARBITRARY_PLACEHOLDERS and is_technical_arbitrary_row(row):
        return True
    if expected_model_type(row.field_type) in {"SubmodelElementCollection", "SubmodelElementList"}:
        return not has_actual_value(row)
    return False


def classify_rows(rows: list[InputRow], entries: list[TemplateEntry]) -> list[RowClassification]:
    by_id = {}
    by_semantic = {}
    for entry in entries:
        if entry.id_short:
            by_id.setdefault(entry.id_short, []).append(entry)
        if entry.semantic_id:
            by_semantic.setdefault(normalized_semantic(entry.semantic_id), []).append(entry)

    classifications: list[RowClassification] = []
    for row in rows:
        semantic_matches = by_semantic.get(normalized_semantic(row.semantic_id), []) if row.semantic_id else []
        id_matches = by_id.get(row.id_short, []) if row.id_short else []
        exact_matches = [
            entry for entry in semantic_matches if not row.id_short or entry.id_short == row.id_short
        ] or id_matches
        template_path = exact_matches[0].path if exact_matches else ""

        if is_template_scaffold_row(row):
            classifications.append(
                RowClassification(
                    row=row,
                    classification="template_scaffold",
                    reason="Excel row describes IDTA template structure or an arbitrary placeholder, not product data.",
                    template_path=template_path,
                    final_path="",
                )
            )
        elif is_technical_arbitrary_row(row):
            final_path = f"TechnicalPropertyAreas/[]/Section/{aas_idshort(row.id_short, 'ArbitraryProperty')}"
            reason = "Excel row is allowed under the template's General/Arbitrary extension point."
            if not has_actual_value(row):
                reason += " Actual Value is missing and will be preserved with SourceValueStatus."
            classifications.append(
                RowClassification(
                    row=row,
                    classification="allowed_arbitrary_extension",
                    reason=reason,
                    template_path=template_path,
                    final_path=final_path,
                )
            )
        elif exact_matches:
            classifications.append(
                RowClassification(
                    row=row,
                    classification="standard_template_element",
                    reason="Excel row matches an explicit template element by semanticId and/or idShort.",
                    template_path=template_path,
                    final_path=template_path,
                )
            )
        else:
            classifications.append(
                RowClassification(
                    row=row,
                    classification="unmapped_excel_row",
                    reason="No matching template element or allowed arbitrary extension was found.",
                    template_path="",
                    final_path="",
                )
            )
    return classifications


def row_classification_record(classification: RowClassification) -> dict[str, Any]:
    row = classification.row
    return {
        "sheet": row.sheet,
        "row": row.row,
        "idShort": row.id_short,
        "fieldType": row.field_type,
        "semanticId": row.semantic_id,
        "actualValue": row.actual_value,
        "sectionPath": list(row.section_path),
        "classification": classification.classification,
        "reason": classification.reason,
        "templatePath": classification.template_path,
        "finalAasPath": classification.final_path,
        "actualValuePresent": has_actual_value(row),
    }


def match_record(row: InputRow, candidate: Candidate | None, score_value: int, mode: str) -> dict[str, Any]:
    return {
        "sheet": row.sheet,
        "row": row.row,
        "idShort": row.id_short,
        "semanticId": row.semantic_id,
        "value": row.actual_value,
        "mode": mode,
        "matchScore": score_value,
        "target": None
        if candidate is None
        else {
            "path": candidate.path,
            "idShort": candidate.id_short,
            "semanticId": candidate.semantic_id,
            "modelType": candidate.model_type,
            "valueType": candidate.value_type,
        },
    }


def string_property(id_short: str, value: Any, semantic: str | None = None) -> dict[str, Any]:
    element: dict[str, Any] = {
        "idShort": aas_idshort(id_short, "Property"),
        "modelType": "Property",
        "valueType": "xs:string",
        "value": text(value),
    }
    if semantic:
        element["semanticId"] = {
            "type": "ExternalReference",
            "keys": [{"type": "GlobalReference", "value": semantic}],
        }
    return element


def missing_value_qualifier() -> dict[str, Any]:
    return {
        "type": "SourceValueStatus",
        "valueType": "xs:string",
        "value": "MissingInExcel",
    }


def dummy_generated_qualifier() -> dict[str, Any]:
    return {
        "type": "SourceValueStatus",
        "valueType": "xs:string",
        "value": "DummyGenerated",
    }


def add_source_value_status(element: dict[str, Any], status: str) -> None:
    qualifiers = element.setdefault("qualifiers", [])
    for item in qualifiers:
        if isinstance(item, dict) and item.get("type") == "SourceValueStatus":
            item["value"] = status
            return
    qualifiers.append(
        dummy_generated_qualifier() if status == "DummyGenerated" else missing_value_qualifier()
    )


def add_missing_value_status(element: dict[str, Any]) -> None:
    add_source_value_status(element, "MissingInExcel")


def has_element_value(element: dict[str, Any]) -> bool:
    model_type = text(element.get("modelType"))
    if model_type == "Range":
        return text(element.get("min")) != "" or text(element.get("max")) != ""
    if model_type in {"Property", "File", "Blob", "ReferenceElement"}:
        return text(element.get("value")) != ""
    if model_type == "MultiLanguageProperty":
        value = element.get("value")
        return isinstance(value, list) and any(text(item.get("text")) for item in value if isinstance(item, dict))
    return True


def has_source_value_status(element: dict[str, Any]) -> bool:
    for qualifier in element.get("qualifiers", []) or []:
        if isinstance(qualifier, dict) and qualifier.get("type") == "SourceValueStatus":
            return True
    return False


def subtree_has_instance_content(element: dict[str, Any]) -> bool:
    if has_source_value_status(element):
        return True

    model_type = text(element.get("modelType"))
    if model_type == "Range":
        return text(element.get("min")) != "" or text(element.get("max")) != ""
    if model_type in {"Property", "File", "Blob", "ReferenceElement"}:
        return text(element.get("value")) != ""
    if model_type == "MultiLanguageProperty":
        value = element.get("value")
        return isinstance(value, list) and any(
            text(item.get("text")) for item in value if isinstance(item, dict)
        )

    return any(subtree_has_instance_content(child) for child in children(element))


def prune_uninstantiated_optional_branches(
    element: dict[str, Any],
    path: str = "",
) -> list[dict[str, str]]:
    current_id = text(element.get("idShort")) or "[]"
    current_path = f"{path}/{current_id}" if path else current_id
    records: list[dict[str, str]] = []

    for field in ("submodelElements", "value"):
        values = element.get(field)
        if not isinstance(values, list):
            continue

        kept = []
        for child in values:
            if not isinstance(child, dict) or "modelType" not in child:
                kept.append(child)
                continue

            records.extend(prune_uninstantiated_optional_branches(child, current_path))
            child_id = text(child.get("idShort")) or "[]"
            child_path = f"{current_path}/{child_id}"
            if (
                cardinality(child) in OPTIONAL_CARDINALITIES
                and not subtree_has_instance_content(child)
            ):
                records.append(
                    {
                        "path": child_path,
                        "idShort": child_id,
                        "modelType": text(child.get("modelType")),
                        "cardinality": cardinality(child),
                        "reason": "Optional template branch had no mapped Excel values.",
                    }
                )
                continue
            kept.append(child)

        element[field] = kept

    return records


def dummy_value_for(value_type: str) -> str:
    if value_type == "xs:boolean":
        return "false"
    if value_type in {"xs:integer", "xs:int", "xs:long", "xs:short", "xs:byte", "xs:nonNegativeInteger", "xs:nonPositiveInteger"}:
        return "-1"
    if value_type in {"xs:decimal", "xs:double", "xs:float"}:
        return "-1.0"
    if value_type == "xs:date":
        return "1970-01-01"
    if value_type == "xs:dateTime":
        return "1970-01-01T00:00:00"
    if value_type == "xs:anyURI":
        return "https://example.org/dummy/not-available"
    return "Not Available"


def fill_dummy_value(element: dict[str, Any]) -> None:
    model_type = text(element.get("modelType"))
    value_type = text(element.get("valueType")) or "xs:string"
    if model_type == "MultiLanguageProperty":
        element["value"] = [{"language": "en", "text": "Not Available"}]
    elif model_type == "File":
        element["contentType"] = text(element.get("contentType")) or "text/plain"
        element["value"] = "/dummy/not-available.txt"
    elif model_type == "Property":
        element["value"] = dummy_value_for(value_type)
    elif model_type == "Range":
        dummy = dummy_value_for(value_type)
        element["min"] = dummy
        element["max"] = dummy
    else:
        return
    add_source_value_status(element, "DummyGenerated")


def fill_mandatory_missing_value(element: dict[str, Any], policy: dict[str, str]) -> str:
    if policy["mandatoryMissingValue"] == "error":
        return "error"
    if policy["mandatoryMissingValue"] == "dummy":
        fill_dummy_value(element)
        return "dummy"

    model_type = text(element.get("modelType"))
    if model_type == "MultiLanguageProperty":
        element["value"] = [{"language": "en", "text": ""}]
    elif model_type == "File":
        element["contentType"] = text(element.get("contentType")) or "text/plain"
        element["value"] = ""
    elif model_type == "Property":
        element["value"] = ""
    elif model_type == "Range":
        element["min"] = ""
        element["max"] = ""
    add_missing_value_status(element)
    return "preserve-empty"


def add_mandatory_dummy_values(
    element: dict[str, Any],
    policy: dict[str, str] | None = None,
    path: str = "",
    skip_empty_optional_branches: bool = False,
) -> list[dict[str, Any]]:
    policy = policy or DEFAULT_GENERATION_POLICY
    id_short = text(element.get("idShort")) or "[]"
    current_path = f"{path}/{id_short}" if path else id_short
    records: list[dict[str, Any]] = []
    if (
        path
        and skip_empty_optional_branches
        and cardinality(element) in OPTIONAL_CARDINALITIES
        and not subtree_has_instance_content(element)
    ):
        return records

    for child in children(element):
        records.extend(
            add_mandatory_dummy_values(
                child,
                policy,
                current_path,
                skip_empty_optional_branches,
            )
        )

    model_type = text(element.get("modelType"))
    if model_type not in {"Property", "MultiLanguageProperty", "File", "Range"}:
        return records
    if cardinality(element) != "One" or has_element_value(element):
        return records

    action = fill_mandatory_missing_value(element, policy)
    record = {
        "path": current_path,
        "idShort": id_short,
        "modelType": model_type,
        "valueType": text(element.get("valueType")),
        "policy": policy["mandatoryMissingValue"],
        "reason": "Mandatory template element had no Excel value.",
    }
    if action == "error":
        record["reason"] += " Generation policy requires an error."
        records.append(record)
        raise ValueError(
            "Mandatory value missing: "
            f"path={record['path']} idShort={record['idShort']} "
            f"modelType={record['modelType']} valueType={record['valueType']}"
        )
    if action == "dummy":
        record["reason"] += " Dummy value generated."
    else:
        record["reason"] += " Empty value preserved."
    records.append(record)
    warning(
        "MANDATORY missing: "
        f"path={record['path']} idShort={record['idShort']} "
        f"modelType={record['modelType']} valueType={record['valueType']} "
        f"policy={record['policy']}"
    )
    return records


def arbitrary_element_from_row(row: InputRow) -> dict[str, Any]:
    model_type = expected_model_type(row.field_type) or "Property"
    id_short = aas_idshort(row.id_short, "ArbitraryProperty")
    base: dict[str, Any] = {
        "category": "PARAMETER",
        "idShort": id_short,
        "description": [{"language": "en", "text": row.id_short.replace("_", " ")}],
        "semanticId": {
            "type": "ExternalReference",
            "keys": [{"type": "GlobalReference", "value": GENERIC_ARBITRARY_SEMANTIC}],
        },
        "modelType": model_type,
    }
    if model_type == "MultiLanguageProperty":
        value, language = split_lang(row.actual_value)
        base["value"] = [{"language": language, "text": value}]
    elif model_type == "File":
        base["contentType"] = infer_content_type(row.actual_value)
        base["value"] = row.actual_value
    elif model_type == "Range":
        base["valueType"] = infer_value_type(row.field_type)
        base["min"] = row.actual_value
        base["max"] = row.actual_value
    elif model_type == "SubmodelElementList":
        base["typeValueListElement"] = "SubmodelElementCollection"
        base["value"] = []
    elif model_type == "SubmodelElementCollection":
        base["value"] = []
    else:
        base["modelType"] = "Property"
        base["valueType"] = infer_value_type(row.field_type)
        base["value"] = row.actual_value
    if not has_actual_value(row):
        add_missing_value_status(base)
    return base


def append_technical_arbitrary_properties(
    submodel: dict[str, Any],
    classifications: list[RowClassification],
) -> list[dict[str, Any]]:
    target = find_element_by_idshort(submodel, "TechnicalPropertyAreas")
    if target is None:
        return []

    area_items = children(target)
    if not area_items:
        return []
    area = area_items[0]

    section = find_element_by_idshort(area, "Section")
    if section is None:
        section = {
            "idShort": "Section",
            "semanticId": {
                "type": "ExternalReference",
                "keys": [{"type": "GlobalReference", "value": GENERIC_ARBITRARY_SEMANTIC}],
            },
            "value": [],
            "modelType": "SubmodelElementCollection",
        }
        area.setdefault("value", []).append(section)
    area["value"] = [
        item
        for item in area.get("value", [])
        if item is section
        or not (isinstance(item, dict) and item.get("idShort") in TECHNICAL_ARBITRARY_PLACEHOLDERS - {"Section"})
    ]

    section_values = [
        item
        for item in section.get("value", [])
        if not (isinstance(item, dict) and item.get("idShort") in TECHNICAL_ARBITRARY_PLACEHOLDERS)
    ]
    section["value"] = section_values
    inserted: list[dict[str, Any]] = []
    for classification in classifications:
        row = classification.row
        if classification.classification != "allowed_arbitrary_extension":
            continue
        element = arbitrary_element_from_row(row)
        section_values.append(element)
        inserted.append(
            {
                "sheet": row.sheet,
                "row": row.row,
                "idShort": row.id_short,
                "semanticId": row.semantic_id,
                "value": row.actual_value,
                "mode": "technical-arbitrary-expanded",
                "target": {
                    "path": "TechnicalPropertyAreas/[]/Section/" + element["idShort"],
                    "idShort": element["idShort"],
                    "semanticId": GENERIC_ARBITRARY_SEMANTIC,
                    "modelType": element["modelType"],
                    "valueType": element.get("valueType", ""),
                },
            }
        )
    if not section_values:
        submodel["submodelElements"] = [
            element
            for element in submodel.get("submodelElements", [])
            if element is not target
        ]
    return inserted


def append_nameplate_address_information(
    submodel: dict[str, Any],
    rows: list[InputRow],
) -> tuple[list[dict[str, Any]], list[InputRow]]:
    address = find_element_by_idshort(submodel, "AddressInformation")
    address_rows = [
        row
        for row in rows
        if row.id_short in {"Street", "Zipcode", "CityTown", "NationalCode"}
        and meaningful_row(row)
    ]
    if address is None or not address_rows:
        return [], rows

    address_values = address.setdefault("value", [])
    inserted: list[dict[str, Any]] = []
    consumed = {row.row for row in address_rows}
    for row in address_rows:
        value, language = split_lang(row.actual_value)
        element = {
            "idShort": row.id_short,
            "semanticId": {
                "type": "ExternalReference",
                "keys": [{"type": "GlobalReference", "value": row.semantic_id}],
            },
            "value": [{"language": language, "text": value}],
            "modelType": "MultiLanguageProperty",
        }
        address_values.append(element)
        inserted.append(
            {
                "sheet": row.sheet,
                "row": row.row,
                "idShort": row.id_short,
                "semanticId": row.semantic_id,
                "value": row.actual_value,
                "mode": "nameplate-address-expanded",
                "target": {
                    "path": "AddressInformation/" + row.id_short,
                    "idShort": row.id_short,
                    "semanticId": row.semantic_id,
                    "modelType": "MultiLanguageProperty",
                    "valueType": "",
                },
            }
        )

    remaining = [row for row in rows if row.row not in consumed]
    return inserted, remaining


def fill_handover_documents(
    submodel: dict[str, Any],
    rows: list[InputRow],
    policy: dict[str, str],
) -> tuple[list[dict[str, Any]], list[InputRow]]:
    documents = find_element_by_idshort(submodel, "Documents")
    if documents is None:
        return fill_standard_matches(submodel, rows, policy)
    template_items = children(documents)
    if not template_items:
        return fill_standard_matches(submodel, rows, policy)

    groups = group_handover_rows(rows)
    if not groups:
        return [], []

    documents["value"] = []
    matched: list[dict[str, Any]] = []
    unmatched: list[InputRow] = []
    for index, group in enumerate(groups):
        document_item = copy.deepcopy(template_items[0])
        clear_values(document_item)
        documents["value"].append(document_item)

        group_candidates = candidate_elements(document_item)
        used_paths: set[str] = set()
        for row in group:
            if not row_can_enter_mapping(row, policy):
                continue
            candidate, match_score = best_candidate(row, group_candidates, used_paths)
            if candidate is None:
                unmatched.append(row)
                continue
            fill_element(candidate.element, row, policy)
            used_paths.add(candidate.path)
            record = match_record(row, candidate, match_score, f"handover-document-{index}")
            matched.append(record)

    return matched, unmatched


def group_handover_rows(rows: list[InputRow]) -> list[list[InputRow]]:
    groups: list[list[InputRow]] = []
    current: list[InputRow] = []
    for row in rows:
        if row.id_short == "DocumentDomainId" and current:
            groups.append(current)
            current = []
        if meaningful_row(row):
            current.append(row)
    if current:
        groups.append(current)
    return groups


def find_element_by_idshort(element: dict[str, Any], id_short: str) -> dict[str, Any] | None:
    if element.get("idShort") == id_short:
        return element
    for child in children(element):
        found = find_element_by_idshort(child, id_short)
        if found is not None:
            return found
    return None


def build_shell(
    product_name: str,
    product_slug: str,
    asset_id: str,
    submodels: list[dict[str, Any]],
    config: dict[str, Any],
    thumbnail: dict[str, str] | None = None,
) -> dict[str, Any]:
    asset_config = config.get("asset", {})
    aas_id_prefix = text(asset_config.get("aasIdPrefix")) or "https://example.org/aas"
    asset_id_prefix = text(asset_config.get("assetIdPrefix")) or "https://example.org/assets"
    asset_information = {
        "assetKind": "Type",
        "globalAssetId": asset_id or f"{asset_id_prefix.rstrip('/')}/{product_slug}",
        "assetType": text(asset_config.get("assetType")) or "Product",
    }
    if thumbnail:
        asset_information["defaultThumbnail"] = thumbnail
    return {
        "idShort": aas_idshort(product_name, text(asset_config.get("fallbackIdShort")) or "Product"),
        "id": f"{aas_id_prefix.rstrip('/')}/{product_slug}",
        "assetInformation": asset_information,
        "submodels": [
            {"type": "ModelReference", "keys": [{"type": "Submodel", "value": item["id"]}]}
            for item in submodels
        ],
        "modelType": "AssetAdministrationShell",
    }


def load_reference(reference_dir: Path, file_name: str) -> dict[str, Any]:
    return load_json(reference_dir / file_name)


def review_payload(
    workbook: str,
    product: str,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "workbook": workbook,
        "productSlug": product,
        "sheet": report["sheet"],
        "submodel": report["submodel"],
        "referenceFile": report["referenceFile"],
        "generationPolicy": report["generationPolicy"],
        "count": len(rows),
        "rows": rows,
    }


def write_step2_review_files(
    workbook_output_dir: Path,
    workbook: str,
    product_slug: str,
    submodel_report: dict[str, Any],
) -> None:
    review_dir = workbook_output_dir / "review" / slug(submodel_report["sheet"])
    review_files = {
        "unmapped-rows.json": submodel_report["unmatchedRows"],
        "preclassified-unmapped-rows.json": [
            row
            for row in submodel_report["rowClassifications"]
            if row["classification"] == "unmapped_excel_row"
        ],
        "dummy-generated.json": submodel_report["dummyGeneratedRows"],
        "skipped-template-scaffold.json": [
            row
            for row in submodel_report["rowClassifications"]
            if row["classification"] == "template_scaffold"
        ],
        "optional-pruned.json": submodel_report["optionalPrunedRows"],
        "matched-rows.json": submodel_report["matchedRows"],
    }
    for file_name, rows in review_files.items():
        write_json(
            review_dir / file_name,
            review_payload(workbook, product_slug, submodel_report, rows),
        )


def should_write_review_files(policy: dict[str, str], submodel_report: dict[str, Any]) -> bool:
    if policy["reviewFiles"] == "off":
        return False
    if policy["reviewFiles"] == "always":
        return True
    return bool(
        submodel_report["unmatchedCount"]
        or submodel_report["dummyGeneratedCount"]
        or submodel_report["optionalPrunedCount"]
    )


def should_log(policy: dict[str, str], minimum: str = "normal") -> bool:
    levels = {"quiet": 0, "normal": 1, "detailed": 2}
    return levels[policy["logLevel"]] >= levels[minimum]


def build_workbook(
    workbook_dir: Path,
    reference_dir: Path,
    output_dir: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    workbook = load_json(workbook_dir / "workbook.json")
    mappings = sheet_templates(config)
    policy = generation_policy(config)
    all_rows: list[InputRow] = []
    sheet_rows: dict[str, list[InputRow]] = {}
    for sheet_name in mappings:
        sheet_file = workbook_dir / f"{slug(sheet_name)}.json"
        rows = load_rows(load_json(sheet_file))
        sheet_rows[sheet_name] = rows
        all_rows.extend(rows)

    product_name = (
        value_for(all_rows, "ManufacturerProductType")
        or value_for(all_rows, "ManufacturerProductDesignation")
        or workbook["workbook"].removesuffix(".xlsx")
    )
    product_slug = slug(product_name)
    asset_id = value_for(all_rows, "URIOfTheProduct")

    submodels: list[dict[str, Any]] = []
    concept_descriptions: dict[str, dict[str, Any]] = {}
    report = {
        "workbook": workbook["workbook"],
        "source": workbook["source"],
        "company": config.get("company"),
        "companyConfig": config.get("_path"),
        "referenceDir": str(reference_dir),
        "generationPolicy": policy,
        "productSlug": product_slug,
        "submodels": [],
    }

    workbook_output_dir = output_dir / workbook_dir.name
    submodel_id_prefix = (
        text(config.get("asset", {}).get("submodelIdPrefix"))
        or "https://example.org/submodels"
    )
    for sheet_name, (submodel_id_short, reference_file) in mappings.items():
        reference = load_reference(reference_dir, reference_file)
        submodel = copy.deepcopy(reference["submodels"][0])
        reference_entries = template_index(reference["submodels"][0])
        submodel["id"] = f"{submodel_id_prefix.rstrip('/')}/{product_slug}/{slug(submodel_id_short)}"
        submodel["kind"] = "Instance"
        clear_values(submodel)

        rows = sheet_rows[sheet_name]
        classifications = classify_rows(rows, reference_entries)
        if submodel_id_short == "HandoverDocumentation":
            matched, unmatched = fill_handover_documents(submodel, rows, policy)
        else:
            matched, unmatched = fill_standard_matches(submodel, rows, policy)
        inserted: list[dict[str, Any]] = []
        expanded_unmatched = unmatched
        if submodel_id_short == "Nameplate":
            nameplate_inserted, expanded_unmatched = append_nameplate_address_information(
                submodel, unmatched
            )
            inserted.extend(nameplate_inserted)
        if submodel_id_short == "TechnicalData":
            inserted = append_technical_arbitrary_properties(submodel, classifications)
            expanded_unmatched = [row for row in unmatched if not is_technical_arbitrary_row(row)]
        pruned_records: list[dict[str, str]] = []
        if policy["optionalEmptyTemplateBranches"] == "prune":
            pruned_records = prune_uninstantiated_optional_branches(submodel)
        if pruned_records and should_log(policy):
            classified(
                f"optional pruned {workbook_dir.name}/{sheet_name}: "
                f"count={len(pruned_records)} details=mapping-report.json"
            )
        dummy_records = add_mandatory_dummy_values(
            submodel,
            policy,
            skip_empty_optional_branches=policy["optionalEmptyTemplateBranches"] == "keep-empty",
        )
        submodels.append(submodel)
        for concept in reference.get("conceptDescriptions", []):
            concept_descriptions.setdefault(concept["id"], concept)
        classification_records = [
            row_classification_record(classification) for classification in classifications
        ]
        unresolved_rows = [
            {
                "sheet": row.sheet,
                "row": row.row,
                "idShort": row.id_short,
                "semanticId": row.semantic_id,
                "value": row.actual_value,
            }
            for row in expanded_unmatched
            if meaningful_row(row)
        ]
        classification_counts: dict[str, int] = {}
        for record in classification_records:
            classification_counts[record["classification"]] = (
                classification_counts.get(record["classification"], 0) + 1
            )
        message = (
            "classified "
            f"{workbook_dir.name}/{sheet_name}: "
            + ", ".join(
                f"{'preclassified_unmapped_excel_row' if name == 'unmapped_excel_row' else name}={count}"
                for name, count in sorted(classification_counts.items())
            )
            + f", unresolved_excel_row={len(unresolved_rows)}"
        )
        if unresolved_rows:
            warning(message)
        elif should_log(policy):
            classified(message)
        if should_log(policy, "detailed"):
            for row in unresolved_rows:
                warning(
                    "unresolved row: "
                    f"sheet={row['sheet']} row={row['row']} "
                    f"idShort={row['idShort']} value={row['value']!r}"
                )
            for record in dummy_records:
                warning(
                    "mandatory record: "
                    f"path={record['path']} idShort={record['idShort']} "
                    f"policy={record['policy']}"
                )

        submodel_report = {
            "sheet": sheet_name,
            "submodel": submodel_id_short,
            "referenceFile": reference_file,
            "generationPolicy": policy,
            "templateEntryCount": len(reference_entries),
            "classificationCounts": classification_counts,
            "rowClassifications": classification_records,
            "matchedCount": len(matched),
            "expandedCount": len(inserted),
            "optionalPrunedCount": len(pruned_records),
            "optionalPrunedRows": pruned_records,
            "dummyGeneratedCount": len(dummy_records),
            "dummyGeneratedRows": dummy_records,
            "unmatchedCount": len(unresolved_rows),
            "matchedRows": matched + inserted,
            "unmatchedRows": unresolved_rows,
            "skippedRows": [
                {
                    "sheet": row.sheet,
                    "row": row.row,
                    "idShort": row.id_short,
                    "semanticId": row.semantic_id,
                    "value": row.actual_value,
                }
                for row in rows
                if not meaningful_row(row)
            ],
        }
        report["submodels"].append(submodel_report)
        write_json(workbook_output_dir / f"{slug(sheet_name)}.json", {"submodels": [submodel]})
        if should_write_review_files(policy, submodel_report):
            write_step2_review_files(
                workbook_output_dir,
                workbook["workbook"],
                product_slug,
                submodel_report,
            )

    environment = {
        "assetAdministrationShells": [
            build_shell(
                product_name,
                product_slug,
                asset_id,
                submodels,
                config,
                thumbnail_for(all_rows),
            )
        ],
        "submodels": submodels,
        "conceptDescriptions": list(concept_descriptions.values()),
    }
    normalize_instance_payload(environment)
    remove_empty_idshorts(environment)
    write_json(workbook_output_dir / "environment.json", environment)
    write_json(workbook_output_dir / "mapping-report.json", report)
    return {
        "workbook": workbook["workbook"],
        "output": str(workbook_output_dir),
        "submodels": [
            {
                "submodel": item["submodel"],
                "matchedCount": item["matchedCount"],
                "expandedCount": item["expandedCount"],
                "unmatchedCount": item["unmatchedCount"],
            }
            for item in report["submodels"]
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--company-config", type=Path, default=DEFAULT_COMPANY_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_company_config(args.company_config)
    summaries = []
    for workbook_dir in sorted(args.input_dir.iterdir()):
        if not workbook_dir.is_dir() or workbook_dir.name == "reference":
            continue
        summaries.append(build_workbook(workbook_dir, args.reference_dir, args.output_dir, config))
    write_json(args.output_dir / "summary.json", {"workbooks": summaries})


if __name__ == "__main__":
    main()
