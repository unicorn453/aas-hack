from pathlib import Path

from excel_to_aasx.validate import validate_aas_core_python


SDK_PATH = Path("third_party/aas-core-works/aas-core3.0-python")


def test_aas_core_python_accepts_minimal_environment() -> None:
    result = validate_aas_core_python({}, SDK_PATH)

    assert result["issueCounts"] == {"error": 0, "warning": 0, "info": 0}


def test_aas_core_python_reports_duplicate_languages() -> None:
    environment = {
        "conceptDescriptions": [
            {
                "id": "https://example.org/concept/example",
                "modelType": "ConceptDescription",
                "displayName": [
                    {"language": "en", "text": "Name"},
                    {"language": "en", "text": "Duplicate"},
                ],
            }
        ]
    }

    result = validate_aas_core_python(environment, SDK_PATH)

    assert result["issueCounts"]["error"] == 1
    assert result["issues"][0]["code"] == "aas-core-python-verification"
    assert result["issues"][0]["message"] == "Display name must specify unique languages."
