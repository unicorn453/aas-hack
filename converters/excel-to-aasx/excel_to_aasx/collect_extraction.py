"""Collect Step 1 Excel extraction files into one review folder."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from excel_to_aasx.company_config import load_company_config
from excel_to_aasx.logging import generated


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    generated(path)


def copy_workbook_extraction(source: Path, target: Path) -> list[str]:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for source_file in sorted(source.glob("*.json")):
        target_file = target / source_file.name
        shutil.copy2(source_file, target_file)
        copied.append(source_file.name)
    return copied


def collect_company(config_path: Path, output_root: Path) -> dict[str, Any]:
    config = load_company_config(config_path)
    company = str(config["company"])
    generated_root = Path(config.get("outputRoot") or f"data/generated/{company}")
    step1_root = generated_root / "xlsx-json-step1"
    if not step1_root.is_dir():
        raise FileNotFoundError(f"missing Step 1 extraction folder: {step1_root}")

    company_target = output_root / "xlsx-json-step1" / company
    workbooks = []
    for workbook_dir in sorted(path for path in step1_root.iterdir() if path.is_dir()):
        copied = copy_workbook_extraction(workbook_dir, company_target / workbook_dir.name)
        workbooks.append(
            {
                "workbook": workbook_dir.name,
                "source": str(workbook_dir),
                "target": str(company_target / workbook_dir.name),
                "files": copied,
            }
        )
        print(f"collected {company}/{workbook_dir.name}: {len(copied)} JSON files")

    return {
        "company": company,
        "companyConfig": str(config_path),
        "sourceStep1Root": str(step1_root),
        "targetRoot": str(company_target),
        "workbooks": workbooks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--company-config",
        type=Path,
        action="append",
        required=True,
        help="Company config to collect. Repeat for multiple companies.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/extraction"),
        help="Folder that receives the neat extraction review tree.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summaries = [collect_company(path, args.output_root) for path in args.company_config]
    write_json(
        args.output_root / "manifest.json",
        {
            "purpose": "Consolidated review copy of Step 1 Excel extraction JSON files.",
            "canonicalSource": "data/generated/<company>/xlsx-json-step1",
            "companies": summaries,
        },
    )


if __name__ == "__main__":
    main()
