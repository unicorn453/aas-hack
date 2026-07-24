"""Validate company step-2 AAS JSON against reference-shaped expectations."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from excel_to_aasx.company_config import DEFAULT_COMPANY_CONFIG, load_company_config, reference_files
from excel_to_aasx.logging import generated, warning


DEFAULT_AAS_CORE_SCHEMA = Path(
    "third_party/aas-core-works/aas-core-codegen/dev/test_data/main/jsonschema/"
    "expected/aas_core_meta.v3/expected_output/schema.json"
)
DEFAULT_AAS_CORE_PYTHON = Path("third_party/aas-core-works/aas-core3.0-python")
THIRD_PARTY_LOCK = Path("third_party/references.lock.json")
FORBIDDEN_KEYS = {
    "sheet",
    "row",
    "workbook",
    "actualValue",
    "allColumns",
    "parsedRows",
    "rawRows",
    "completeExtraction",
}
ALLOWED_EXPANSIONS = {
    "Nameplate": {
        "AddressInformation/Street",
        "AddressInformation/Zipcode",
        "AddressInformation/CityTown",
        "AddressInformation/NationalCode",
    },
}
TECHNICAL_ARBITRARY_PREFIX = "TechnicalPropertyAreas/[]/Section/"
GENERIC_ARBITRARY_SEMANTIC = "https://admin-shell.io/SMT/General/Arbitrary"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    generated(path)


def children(element: dict[str, Any]) -> list[dict[str, Any]]:
    value = element.get("value")
    if isinstance(value, list):
        return [
            item
            for item in value
            if isinstance(item, dict) and "modelType" in item
        ]
    submodel_elements = element.get("submodelElements")
    if isinstance(submodel_elements, list):
        return submodel_elements
    return []


def semantic_id(element: dict[str, Any]) -> str:
    keys = (element.get("semanticId") or {}).get("keys") or []
    return str(keys[-1].get("value", "")).strip() if keys else ""


def cardinality(element: dict[str, Any]) -> str:
    for qualifier in element.get("qualifiers", []) or []:
        if qualifier.get("type") == "SMT/Cardinality":
            return str(qualifier.get("value", "")).strip()
    return ""


def element_path(
    element: dict[str, Any],
    parent: str = "",
    parent_model_type: str = "",
) -> str:
    id_short = "[]" if parent_model_type == "SubmodelElementList" else element.get("idShort") or "[]"
    return f"{parent}/{id_short}" if parent else id_short


def collect_elements(
    element: dict[str, Any],
    parent: str = "",
    parent_model_type: str = "",
) -> list[tuple[str, dict[str, Any]]]:
    path = element_path(element, parent, parent_model_type)
    result = [(path, element)]
    for child in children(element):
        result.extend(collect_elements(child, path, str(element.get("modelType", ""))))
    return result


def canonical_path(path: str) -> str:
    parts = []
    previous = None
    for part in path.split("/"):
        if part == previous and part not in {"[]"}:
            continue
        parts.append(part)
        previous = part
    return "/".join(parts)


def duplicate_suffix_base_path(path: str) -> str | None:
    parts = path.split("/")
    if not parts:
        return None
    match = re.match(r"^(.*)_\d+$", parts[-1])
    if not match:
        return None
    parts[-1] = match.group(1)
    return "/".join(parts)


def reference_paths(reference_submodel: dict[str, Any]) -> set[str]:
    return {
        canonical_path(path)
        for element in reference_submodel.get("submodelElements", [])
        for path, _ in collect_elements(element)
    }


def has_value(element: dict[str, Any]) -> bool:
    model_type = element.get("modelType")
    if model_type == "Property":
        return "value" in element and element.get("value") not in {"", None}
    if model_type == "MultiLanguageProperty":
        return bool(element.get("value"))
    if model_type == "File":
        return bool(element.get("value"))
    if model_type == "Range":
        return "min" in element or "max" in element
    return False


def validate_value(value: Any, value_type: str) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    try:
        if value_type in {"xs:decimal", "xs:double", "xs:float"}:
            float(text)
        elif value_type in {"xs:integer", "xs:int", "xs:long"}:
            int(text)
        elif value_type == "xs:boolean":
            if text.lower() not in {"true", "false"}:
                return f"expected boolean, got {text!r}"
        elif value_type == "xs:date":
            datetime.date.fromisoformat(text)
        elif value_type == "xs:dateTime":
            datetime.datetime.fromisoformat(text)
        elif value_type == "xs:anyURI":
            parsed = urlparse(text)
            if not parsed.scheme:
                return f"expected URI with scheme, got {text!r}"
    except ValueError as exc:
        return f"invalid {value_type}: {exc}"
    return None


def scan_forbidden_keys(payload: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_path = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                hits.append(next_path)
            hits.extend(scan_forbidden_keys(value, next_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            hits.extend(scan_forbidden_keys(value, f"{path}[{index}]"))
    return hits


def issue(severity: str, code: str, message: str, path: str = "") -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message, "path": path}


def aas_core_codegen_commit(schema_path: Path) -> str | None:
    if THIRD_PARTY_LOCK.exists():
        lock = load_json(THIRD_PARTY_LOCK)
        commit = (
            lock.get("repositories", {})
            .get("aas-core-codegen", {})
            .get("commit")
        )
        if isinstance(commit, str) and commit:
            return commit

    parts = schema_path.parts
    repo_name = "aas-core-codegen"
    if repo_name not in parts:
        return None
    repo_path = Path(*parts[: parts.index(repo_name) + 1])
    git_path = repo_path / ".git"
    if git_path.is_file():
        content = git_path.read_text(encoding="utf-8").strip()
        if content.startswith("gitdir: "):
            git_path = (repo_path / content.removeprefix("gitdir: ")).resolve()
    head_path = git_path / "HEAD"
    if not head_path.exists():
        return None
    head = head_path.read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref_path = git_path / head.removeprefix("ref: ")
        return ref_path.read_text(encoding="utf-8").strip() if ref_path.exists() else None
    return head


def json_path(path_parts: Any) -> str:
    parts = list(path_parts)
    if not parts:
        return "$"
    result = "$"
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


def validate_aas_core_schema(
    environment: dict[str, Any],
    schema_path: Path | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "enabled": bool(schema_path),
        "schema": str(schema_path) if schema_path else None,
        "source": "aas-core-works/aas-core-codegen generated JSON Schema",
        "commit": aas_core_codegen_commit(schema_path) if schema_path else None,
        "issueCounts": {"error": 0, "warning": 0, "info": 0},
        "issues": [],
    }
    if not schema_path:
        return result
    if not schema_path.exists():
        result["issues"].append(
            issue("error", "aas-core-schema-missing", f"schema not found: {schema_path}")
        )
        result["issueCounts"] = count_by_severity(result["issues"])
        return result

    try:
        from jsonschema import Draft201909Validator
    except ImportError as exc:
        result["issues"].append(
            issue(
                "error",
                "aas-core-schema-validator-unavailable",
                f"jsonschema package is required for aas-core-codegen schema validation: {exc}",
            )
        )
        result["issueCounts"] = count_by_severity(result["issues"])
        return result

    schema = load_json(schema_path)
    validator = Draft201909Validator(schema)
    schema_issues = []
    for validation_error in validator.iter_errors(environment):
        schema_issues.append(
            issue(
                "error",
                "aas-core-schema-violation",
                validation_error.message,
                json_path(validation_error.absolute_path),
            )
        )
        if len(schema_issues) >= 50:
            schema_issues.append(
                issue(
                    "error",
                    "aas-core-schema-violation-limit",
                    "stopped after first 50 aas-core schema errors",
                )
            )
            break
    result["issues"] = schema_issues
    result["issueCounts"] = count_by_severity(schema_issues)
    return result


def validate_aas_core_python(
    environment: dict[str, Any],
    sdk_path: Path | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "enabled": bool(sdk_path),
        "sdk": str(sdk_path) if sdk_path else None,
        "source": "aas-core-works/aas-core3.0-python typed deserialization and verification",
        "version": None,
        "issueCounts": {"error": 0, "warning": 0, "info": 0},
        "issues": [],
    }
    if not sdk_path:
        return result
    if not sdk_path.exists():
        result["issues"].append(
            issue("error", "aas-core-python-missing", f"SDK path not found: {sdk_path}")
        )
        result["issueCounts"] = count_by_severity(result["issues"])
        return result

    sdk_import_path = str(sdk_path.resolve())
    if sdk_import_path not in sys.path:
        sys.path.insert(0, sdk_import_path)

    try:
        import aas_core3
        import aas_core3.jsonization as aas_jsonization
        import aas_core3.verification as aas_verification
    except ImportError as exc:
        result["issues"].append(
            issue(
                "error",
                "aas-core-python-unavailable",
                f"aas-core3.0-python could not be imported from {sdk_path}: {exc}",
            )
        )
        result["issueCounts"] = count_by_severity(result["issues"])
        return result

    result["version"] = getattr(aas_core3, "__version__", None)

    try:
        typed_environment = aas_jsonization.environment_from_jsonable(environment)
    except Exception as exc:
        result["issues"].append(
            issue(
                "error",
                "aas-core-python-deserialization",
                getattr(exc, "cause", str(exc)),
                str(getattr(exc, "path", "")),
            )
        )
        result["issueCounts"] = count_by_severity(result["issues"])
        return result

    sdk_issues = [
        issue(
            "error",
            "aas-core-python-verification",
            verification_error.cause,
            str(verification_error.path),
        )
        for verification_error in aas_verification.verify(typed_environment)
    ]
    result["issues"] = sdk_issues
    result["issueCounts"] = count_by_severity(sdk_issues)
    return result


def validate_submodel(
    generated: dict[str, Any],
    reference: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    id_short = generated.get("idShort", "")

    if generated.get("idShort") != reference.get("idShort"):
        issues.append(issue("error", "idshort-mismatch", "submodel idShort differs from reference"))

    generated_template_id = (generated.get("administration") or {}).get("templateId")
    reference_template_id = (reference.get("administration") or {}).get("templateId")
    if generated_template_id != reference_template_id:
        issues.append(
            issue(
                "error",
                "template-id-mismatch",
                f"expected {reference_template_id}, got {generated_template_id}",
            )
        )

    if semantic_id(generated) != semantic_id(reference):
        issues.append(
            issue(
                "error",
                "semantic-id-mismatch",
                f"expected {semantic_id(reference)}, got {semantic_id(generated)}",
            )
        )

    known_reference_paths = reference_paths(reference)
    for path, element in [
        item
        for root in generated.get("submodelElements", [])
        for item in collect_elements(root)
    ]:
        normalized_path = canonical_path(path)
        duplicate_base_path = duplicate_suffix_base_path(normalized_path)
        known_normalized_path = normalized_path in known_reference_paths or (
            duplicate_base_path is not None and duplicate_base_path in known_reference_paths
        )
        if not known_normalized_path and not allowed_expansion(
            id_short, normalized_path, element
        ):
            issues.append(
                issue(
                    "warning",
                    "non-reference-element",
                    "element is not present in the official reference template",
                    normalized_path,
                )
            )

        model_type = element.get("modelType")
        if model_type == "Property" and has_value(element):
            value_type = element.get("valueType", "")
            value_issue = validate_value(element.get("value"), value_type)
            if value_issue:
                issues.append(issue("error", "invalid-value-type", value_issue, normalized_path))
        elif model_type == "MultiLanguageProperty" and has_value(element):
            for entry in element.get("value", []):
                if not entry.get("language") or "text" not in entry:
                    issues.append(
                        issue(
                            "error",
                            "invalid-multilanguage-value",
                            "MultiLanguageProperty value needs language and text",
                            normalized_path,
                        )
                    )
        elif model_type == "File" and has_value(element):
            if not element.get("contentType"):
                issues.append(issue("error", "missing-content-type", "File has value but no contentType", normalized_path))

        if cardinality(element) == "One" and model_type in {"Property", "File", "MultiLanguageProperty"} and not has_value(element):
            issues.append(
                issue(
                    "info",
                    "unfilled-cardinality-one",
                    "template marks this leaf as cardinality One but no value was supplied",
                    normalized_path,
                )
            )

    return issues


def allowed_expansion(id_short: str, path: str, element: dict[str, Any]) -> bool:
    if path in ALLOWED_EXPANSIONS.get(id_short, set()):
        return True
    if id_short == "TechnicalData" and path.startswith(TECHNICAL_ARBITRARY_PREFIX):
        return semantic_id(element) == GENERIC_ARBITRARY_SEMANTIC
    return False


def validate_workbook(
    workbook_dir: Path,
    reference_dir: Path,
    output_dir: Path,
    aas_core_schema: Path | None,
    aas_core_python: Path | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    environment_path = workbook_dir / "environment.json"
    environment = load_json(environment_path)
    report: dict[str, Any] = {
        "workbook": workbook_dir.name,
        "environment": str(environment_path),
        "company": config.get("company"),
        "companyConfig": config.get("_path"),
        "issues": [],
        "submodels": [],
    }
    report["aasCoreSchema"] = validate_aas_core_schema(environment, aas_core_schema)
    report["issues"].extend(report["aasCoreSchema"]["issues"])
    report["aasCorePython"] = validate_aas_core_python(environment, aas_core_python)
    report["issues"].extend(report["aasCorePython"]["issues"])

    required_top = {"assetAdministrationShells", "submodels", "conceptDescriptions"}
    missing_top = sorted(required_top - set(environment))
    for key in missing_top:
        report["issues"].append(issue("error", "missing-top-level-key", f"missing {key}"))

    forbidden_hits = scan_forbidden_keys(environment)
    for hit in forbidden_hits:
        report["issues"].append(issue("error", "metadata-leak", "step-1/parser metadata leaked into clean AAS output", hit))

    shells = environment.get("assetAdministrationShells", [])
    submodels = environment.get("submodels", [])
    if len(shells) != 1:
        report["issues"].append(issue("error", "shell-count", f"expected one shell, got {len(shells)}"))
    if len(submodels) != 5:
        report["issues"].append(issue("error", "submodel-count", f"expected five submodels, got {len(submodels)}"))

    submodels_by_id = {item.get("id"): item for item in submodels}
    if shells:
        refs = [
            ref.get("keys", [{}])[-1].get("value")
            for ref in shells[0].get("submodels", [])
        ]
        for ref in refs:
            if ref not in submodels_by_id:
                report["issues"].append(issue("error", "broken-shell-reference", f"missing submodel for {ref}"))
        for submodel in submodels:
            if submodel.get("id") not in refs:
                report["issues"].append(issue("error", "unreferenced-submodel", f"shell does not reference {submodel.get('id')}"))

    for submodel in submodels:
        id_short = submodel.get("idShort")
        reference_file = reference_files(config).get(id_short)
        if not reference_file:
            sub_issues = [issue("error", "unknown-submodel", f"no reference configured for {id_short}")]
        else:
            reference = load_json(reference_dir / reference_file)["submodels"][0]
            sub_issues = validate_submodel(submodel, reference)
        report["submodels"].append(
            {
                "idShort": id_short,
                "id": submodel.get("id"),
                "issueCounts": count_by_severity(sub_issues),
                "issues": sub_issues,
            }
        )

    all_issues = report["issues"] + [
        item for sub in report["submodels"] for item in sub["issues"]
    ]
    report["issueCounts"] = count_by_severity(all_issues)
    write_json(output_dir / workbook_dir.name / "validation-report.json", report)
    return {
        "workbook": workbook_dir.name,
        "issueCounts": report["issueCounts"],
        "output": str(output_dir / workbook_dir.name / "validation-report.json"),
    }


def count_by_severity(issues: list[dict[str, str]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for item in issues:
        counts[item.get("severity", "info")] = counts.get(item.get("severity", "info"), 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--aas-core-schema", type=Path, default=DEFAULT_AAS_CORE_SCHEMA)
    parser.add_argument("--aas-core-python", type=Path, default=DEFAULT_AAS_CORE_PYTHON)
    parser.add_argument("--company-config", type=Path, default=DEFAULT_COMPANY_CONFIG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_company_config(args.company_config)
    summaries = []
    for workbook_dir in sorted(args.input_dir.iterdir()):
        if not workbook_dir.is_dir():
            continue
        summaries.append(
            validate_workbook(
                workbook_dir,
                args.reference_dir,
                args.output_dir,
                args.aas_core_schema,
                args.aas_core_python,
                config,
            )
        )
        counts = summaries[-1]["issueCounts"]
        message = (
            f"validated {workbook_dir.name}: "
            f"errors={counts.get('error', 0)}, "
            f"warnings={counts.get('warning', 0)}, "
            f"info={counts.get('info', 0)}"
        )
        if counts.get("error", 0) or counts.get("warning", 0):
            warning(message)
        else:
            print(message, flush=True)
    summary = {"workbooks": summaries}
    write_json(args.output_dir / "summary.json", summary)

    error_count = sum(
        workbook["issueCounts"].get("error", 0)
        for workbook in summaries
    )
    if error_count:
        raise SystemExit(f"validation failed with {error_count} error(s)")


if __name__ == "__main__":
    main()
