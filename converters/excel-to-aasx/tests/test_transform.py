import json

from excel_to_aasx.transform import (
    GENERIC_ARBITRARY_SEMANTIC,
    InputRow,
    RowClassification,
    add_mandatory_dummy_values,
    append_technical_arbitrary_properties,
    build_shell,
    fill_element,
    generation_policy,
    normalize_instance_payload,
    normalize_value,
    prune_uninstantiated_optional_branches,
    thumbnail_for,
    write_step2_review_files,
)


def test_normalize_instance_payload_removes_template_qualifiers() -> None:
    payload = {
        "modelType": "Property",
        "qualifiers": [
            {"type": "SMT/Cardinality", "kind": "TemplateQualifier", "value": "One"},
            {"type": "Runtime", "kind": "ConceptQualifier", "value": "ok"},
            {"type": "Runtime", "kind": "ConceptQualifier", "value": "duplicate"},
        ],
    }

    normalize_instance_payload(payload)

    assert payload["qualifiers"] == [
        {"type": "Runtime", "kind": "ConceptQualifier", "value": "ok"}
    ]


def test_normalize_instance_payload_deduplicates_language_lists() -> None:
    payload = {
        "description": [
            {"language": "en", "text": "First"},
            {"language": "en", "text": "Second"},
        ],
        "shortName": [
            {"language": "en", "text": "Short"},
            {"language": "en", "text": "Duplicate"},
        ],
    }

    normalize_instance_payload(payload)

    assert payload["description"] == [{"language": "en", "text": "First\nSecond"}]
    assert payload["shortName"] == [{"language": "en", "text": "Short"}]


def test_normalize_instance_payload_removes_list_child_idshorts() -> None:
    payload = {
        "modelType": "SubmodelElementList",
        "value": [
            {"modelType": "Property", "idShort": "TemplateChild"},
        ],
    }

    normalize_instance_payload(payload)

    assert "idShort" not in payload["value"][0]


def test_normalize_instance_payload_deduplicates_sibling_idshorts() -> None:
    payload = {
        "modelType": "SubmodelElementCollection",
        "value": [
            {"modelType": "Property", "idShort": "Duplicate"},
            {"modelType": "Property", "idShort": "Duplicate"},
        ],
    }

    normalize_instance_payload(payload)

    assert [item["idShort"] for item in payload["value"]] == ["Duplicate", "Duplicate_2"]


def test_append_technical_arbitrary_properties_removes_template_placeholders() -> None:
    submodel = {
        "submodelElements": [
            {
                "idShort": "TechnicalPropertyAreas",
                "modelType": "SubmodelElementList",
                "value": [
                    {
                        "modelType": "SubmodelElementCollection",
                        "value": [
                            {
                                "idShort": "Section",
                                "modelType": "SubmodelElementCollection",
                                "value": [
                                    {
                                        "idShort": "ArbitraryProperty",
                                        "modelType": "Property",
                                        "valueType": "xs:string",
                                    }
                                ],
                            },
                            {
                                "idShort": "ArbitrarySMC",
                                "modelType": "SubmodelElementCollection",
                                "value": [],
                            },
                        ],
                    }
                ],
            }
        ]
    }
    stroke_row = InputRow(
        sheet="Technical Data",
        row=55,
        id_short="Stroke_per_jaw_mm",
        field_type="String",
        semantic_id=GENERIC_ARBITRARY_SEMANTIC,
        actual_value="6.0",
        section_path=("TechnicalPropertyAreas",),
    )
    missing_row = InputRow(
        sheet="Technical Data",
        row=56,
        id_short="Missing_parameter",
        field_type="String",
        semantic_id=GENERIC_ARBITRARY_SEMANTIC,
        actual_value="",
        section_path=("TechnicalPropertyAreas",),
    )

    append_technical_arbitrary_properties(
        submodel,
        [
            RowClassification(
                row=stroke_row,
                classification="allowed_arbitrary_extension",
                reason="test",
                template_path="TechnicalData/TechnicalPropertyAreas/[]/Section/ArbitraryProperty",
                final_path="TechnicalPropertyAreas/[]/Section/Stroke_per_jaw_mm",
            ),
            RowClassification(
                row=missing_row,
                classification="allowed_arbitrary_extension",
                reason="test",
                template_path="TechnicalData/TechnicalPropertyAreas/[]/Section/ArbitraryProperty",
                final_path="TechnicalPropertyAreas/[]/Section/Missing_parameter",
            )
        ],
    )

    area_values = submodel["submodelElements"][0]["value"][0]["value"]
    assert [item["idShort"] for item in area_values] == ["Section"]
    section = area_values[0]
    assert [item["idShort"] for item in section["value"]] == [
        "Stroke_per_jaw_mm",
        "Missing_parameter",
    ]
    assert section["value"][1]["value"] == ""
    assert section["value"][1]["qualifiers"][0]["value"] == "MissingInExcel"


def test_append_technical_arbitrary_properties_removes_empty_section_without_values() -> None:
    submodel = {
        "submodelElements": [
            {
                "idShort": "TechnicalPropertyAreas",
                "modelType": "SubmodelElementList",
                "value": [
                    {
                        "modelType": "SubmodelElementCollection",
                        "value": [
                            {
                                "idShort": "Section",
                                "modelType": "SubmodelElementCollection",
                                "value": [],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    inserted = append_technical_arbitrary_properties(submodel, [])

    assert inserted == []
    assert submodel["submodelElements"] == []


def test_thumbnail_for_prefers_product_image_over_company_logo() -> None:
    rows = [
        InputRow("Digital Nameplate", 1, "CompanyLogo", "File", "", "https://example.com/logo.png", ()),
        InputRow("Technical Data", 2, "ImageFile", "File", "", "https://example.com/product-FWEBP-B1440", ()),
    ]

    assert thumbnail_for(rows) == {
        "path": "https://example.com/product-FWEBP-B1440",
        "contentType": "image/webp",
    }


def test_build_shell_adds_default_thumbnail_when_available() -> None:
    shell = build_shell(
        "EGP 40-N-N-B",
        "egp-40-n-n-b",
        "https://example.com/product",
        [],
        {"asset": {"aasIdPrefix": "https://example.org/aas", "assetType": "Gripper"}},
        {"path": "https://example.com/product.webp", "contentType": "image/webp"},
    )

    assert shell["assetInformation"]["defaultThumbnail"] == {
        "path": "https://example.com/product.webp",
        "contentType": "image/webp",
    }


def test_fill_element_updates_file_content_type_from_actual_value() -> None:
    element = {"modelType": "File", "contentType": "image/png"}
    row = InputRow("Technical Data", 2, "ImageFile", "File", "", "https://example.com/product.webp", ())

    fill_element(element, row)

    assert element["value"] == "https://example.com/product.webp"
    assert element["contentType"] == "image/webp"


def test_normalize_value_cleans_dummy_and_quotes_any_uri() -> None:
    assert (
        normalize_value("[DUMMY] https://example.com/product file.pdf", "xs:anyURI")
        == "https://example.com/product%20file.pdf"
    )
    assert (
        normalize_value("manual file.pdf (Datenblatt)", "xs:anyURI")
        == "manual%20file.pdf%20(Datenblatt)"
    )


def test_add_mandatory_dummy_values_marks_missing_leaf() -> None:
    submodel = {
        "idShort": "Nameplate",
        "modelType": "Submodel",
        "submodelElements": [
            {
                "idShort": "URIOfTheProduct",
                "modelType": "Property",
                "valueType": "xs:anyURI",
                "qualifiers": [{"type": "SMT/Cardinality", "valueType": "xs:string", "value": "One"}],
            },
            {
                "idShort": "OptionalValue",
                "modelType": "Property",
                "valueType": "xs:string",
                "qualifiers": [{"type": "SMT/Cardinality", "valueType": "xs:string", "value": "ZeroToOne"}],
            },
        ],
    }

    records = add_mandatory_dummy_values(submodel)

    assert records == [
        {
            "path": "Nameplate/URIOfTheProduct",
            "idShort": "URIOfTheProduct",
            "modelType": "Property",
            "valueType": "xs:anyURI",
            "policy": "dummy",
            "reason": "Mandatory template element had no Excel value. Dummy value generated.",
        }
    ]
    mandatory = submodel["submodelElements"][0]
    optional = submodel["submodelElements"][1]
    assert mandatory["value"] == "https://example.org/dummy/not-available"
    assert mandatory["qualifiers"][-1]["value"] == "DummyGenerated"
    assert "value" not in optional


def test_prune_uninstantiated_optional_branches_removes_empty_optional_tree() -> None:
    submodel = {
        "idShort": "CarbonFootprint",
        "modelType": "Submodel",
        "submodelElements": [
            {
                "idShort": "ProductOrSectorSpecificCarbonFootprints",
                "modelType": "SubmodelElementList",
                "qualifiers": [
                    {"type": "SMT/Cardinality", "valueType": "xs:string", "value": "ZeroToOne"}
                ],
                "value": [
                    {
                        "modelType": "SubmodelElementCollection",
                        "value": [
                            {
                                "idShort": "PcfRuleName",
                                "modelType": "Property",
                                "valueType": "xs:string",
                                "qualifiers": [
                                    {"type": "SMT/Cardinality", "valueType": "xs:string", "value": "One"}
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    records = prune_uninstantiated_optional_branches(submodel)

    assert records == [
        {
            "path": "CarbonFootprint/ProductOrSectorSpecificCarbonFootprints",
            "idShort": "ProductOrSectorSpecificCarbonFootprints",
            "modelType": "SubmodelElementList",
            "cardinality": "ZeroToOne",
            "reason": "Optional template branch had no mapped Excel values.",
        }
    ]
    assert submodel["submodelElements"] == []


def test_prune_uninstantiated_optional_branches_keeps_optional_tree_with_value() -> None:
    submodel = {
        "idShort": "CarbonFootprint",
        "modelType": "Submodel",
        "submodelElements": [
            {
                "idShort": "ProductOrSectorSpecificCarbonFootprints",
                "modelType": "SubmodelElementList",
                "qualifiers": [
                    {"type": "SMT/Cardinality", "valueType": "xs:string", "value": "ZeroToOne"}
                ],
                "value": [
                    {
                        "modelType": "SubmodelElementCollection",
                        "value": [
                            {
                                "idShort": "PcfRuleName",
                                "modelType": "Property",
                                "valueType": "xs:string",
                                "value": "ISO 14067",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    records = prune_uninstantiated_optional_branches(submodel)

    assert records == []
    assert submodel["submodelElements"][0]["idShort"] == "ProductOrSectorSpecificCarbonFootprints"


def test_write_step2_review_files_splits_mapping_report_for_review(tmp_path) -> None:
    submodel_report = {
        "sheet": "Carbon Footprint",
        "submodel": "CarbonFootprint",
        "referenceFile": "published/Carbon Footprint/template.json",
        "generationPolicy": generation_policy({}),
        "rowClassifications": [
            {"row": 10, "classification": "template_scaffold"},
            {"row": 11, "classification": "standard_template_element"},
            {"row": 12, "idShort": "Unknown", "classification": "unmapped_excel_row"},
        ],
        "matchedRows": [{"row": 11, "idShort": "PcfCO2eq", "value": "32.09"}],
        "unmatchedRows": [{"row": 13, "idShort": "LateUnmatched", "value": "x"}],
        "dummyGeneratedRows": [{"path": "CarbonFootprint/Mandatory"}],
        "optionalPrunedRows": [{"path": "CarbonFootprint/Optional"}],
    }

    write_step2_review_files(tmp_path, "product.xlsx", "product", submodel_report)

    review_dir = tmp_path / "review" / "carbon-footprint"
    unmapped = json.loads((review_dir / "unmapped-rows.json").read_text())
    preclassified_unmapped = json.loads((review_dir / "preclassified-unmapped-rows.json").read_text())
    scaffold = json.loads((review_dir / "skipped-template-scaffold.json").read_text())
    matched = json.loads((review_dir / "matched-rows.json").read_text())

    assert unmapped["count"] == 1
    assert unmapped["generationPolicy"]["mandatoryMissingValue"] == "dummy"
    assert unmapped["rows"][0]["idShort"] == "LateUnmatched"
    assert preclassified_unmapped["rows"][0]["idShort"] == "Unknown"
    assert scaffold["rows"] == [{"row": 10, "classification": "template_scaffold"}]
    assert matched["rows"][0]["idShort"] == "PcfCO2eq"


def test_generation_policy_merges_defaults_and_validates_values() -> None:
    policy = generation_policy({"generationPolicy": {"reviewFiles": "issues-only"}})

    assert policy["emptyActualValue"] == "skip"
    assert policy["reviewFiles"] == "issues-only"


def test_generation_policy_rejects_unknown_values() -> None:
    try:
        generation_policy({"generationPolicy": {"mandatoryMissingValue": "guess"}})
    except ValueError as error:
        assert "generationPolicy.mandatoryMissingValue" in str(error)
    else:
        raise AssertionError("invalid generation policy should fail")
