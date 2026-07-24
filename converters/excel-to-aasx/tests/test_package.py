from excel_to_aasx.package import (
    aasx_package_path,
    collect_missing_supplementary_files,
    publish_aasx_collection,
)


def test_collect_missing_supplementary_files_ignores_external_urls() -> None:
    payload = {
        "submodels": [
            {
                "modelType": "Submodel",
                "submodelElements": [
                    {
                        "idShort": "ExternalImage",
                        "modelType": "File",
                        "value": "https://example.com/image.webp",
                        "contentType": "image/webp",
                    },
                    {
                        "idShort": "LocalDocument",
                        "modelType": "File",
                        "value": "manual.pdf",
                        "contentType": "application/pdf",
                    },
                ],
            }
        ]
    }

    assert collect_missing_supplementary_files(payload) == [
        {
            "path": "/aasx/files/manual.pdf",
            "originalPath": "manual.pdf",
            "contentType": "application/pdf",
            "reason": "File reference is local/relative but no source file is available; placeholder added to AASX.",
        }
    ]
    local = payload["submodels"][0]["submodelElements"][1]
    assert local["value"] == "/aasx/files/manual.pdf"


def test_aasx_package_path_avoids_double_encoding_and_trailing_dot() -> None:
    assert (
        aasx_package_path("Maintenance%20flowchart%20not%20available.")
        == "/aasx/files/Maintenance%20flowchart%20not%20available"
    )


def test_publish_aasx_collection_copies_files_to_company_generated_root(tmp_path) -> None:
    output_dir = tmp_path / "xlsx-json-step4"
    source_dir = output_dir / "product"
    source_dir.mkdir(parents=True)
    source = source_dir / "product.aasx"
    source.write_bytes(b"aasx")

    published = publish_aasx_collection(
        output_dir,
        [{"workbook": "product", "aasx": str(source)}],
    )

    target = tmp_path / "aasx" / "product.aasx"
    assert target.read_bytes() == b"aasx"
    assert published == [
        {
            "workbook": "product",
            "source": str(source),
            "aasx": str(target),
            "aasxSizeBytes": 4,
        }
    ]
