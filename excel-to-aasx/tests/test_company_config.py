import json

from excel_to_aasx.company_config import load_company_config


def test_load_company_config_merges_format_parent(tmp_path) -> None:
    formats = tmp_path / "formats"
    companies = tmp_path / "companies"
    formats.mkdir()
    companies.mkdir()

    (formats / "format.json").write_text(
        json.dumps(
            {
                "format": "test-format",
                "asset": {"assetType": "Default asset", "fallbackIdShort": "Product"},
                "sheets": [
                    {
                        "sheet": "Technical Data",
                        "submodelIdShort": "TechnicalData",
                        "template": "template.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    company_config = companies / "company.json"
    company_config.write_text(
        json.dumps(
            {
                "extends": "../formats/format.json",
                "company": "acme",
                "asset": {"assetType": "ACME gripper"},
                "workbooks": ["product.xlsx"],
            }
        ),
        encoding="utf-8",
    )

    config = load_company_config(company_config)

    assert config["format"] == "test-format"
    assert config["company"] == "acme"
    assert config["workbooks"] == ["product.xlsx"]
    assert config["sheets"][0]["submodelIdShort"] == "TechnicalData"
    assert config["asset"] == {
        "assetType": "ACME gripper",
        "fallbackIdShort": "Product",
    }
    assert config["_path"] == str(company_config)
