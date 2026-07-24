"""Load company-specific pipeline configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_COMPANY_CONFIG = Path("configs/companies/schunk.json")


def load_company_config(path: Path | None) -> dict[str, Any]:
    config_path = path or DEFAULT_COMPANY_CONFIG
    config = load_config_with_extends(config_path)
    config["_path"] = str(config_path)
    return config


def load_config_with_extends(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    extends = config.pop("extends", None)
    if not extends:
        return config

    parent_path = (path.parent / extends).resolve()
    parent = load_config_with_extends(parent_path)
    return deep_merge(parent, config)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def sheet_templates(config: dict[str, Any]) -> dict[str, tuple[str, str]]:
    return {
        item["sheet"]: (item["submodelIdShort"], item["template"])
        for item in config.get("sheets", [])
    }


def reference_files(config: dict[str, Any]) -> dict[str, str]:
    return {
        item["submodelIdShort"]: item["template"]
        for item in config.get("sheets", [])
    }
