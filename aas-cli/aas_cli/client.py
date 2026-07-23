"""Thin REST client for a BaSyx AAS Environment (and its optional registry)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

import requests
import urllib3

from .auth import get_token
from .config import ServerConfig
from .encoding import encode_id

ACCEPT_BY_FORMAT = {
    "json": "application/json",
    "xml": "application/xml",
    "aasx": "application/asset-administration-shell-package+xml",
}

# /upload throws a 500 (NPE) if the multipart part has no recognized
# Content-Type -- plain `requests` defaults to application/octet-stream,
# so it must be set explicitly per file extension.
UPLOAD_CONTENT_TYPE_BY_SUFFIX = {
    ".json": "application/json",
    ".xml": "application/xml",
    ".aasx": "application/asset-administration-shell-package+xml",
}

ENTITY_PATHS = {
    "shell": "shells",
    "submodel": "submodels",
    "concept-description": "concept-descriptions",
}


class BasyxClient:
    def __init__(self, server: ServerConfig):
        self.server = server
        if not server.verify_tls:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _headers(self, accept: Optional[str] = None) -> dict[str, str]:
        headers = {}
        token = get_token(self.server)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if accept:
            headers["Accept"] = accept
        return headers

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        response = requests.request(
            method, url, headers=headers, verify=self.server.verify_tls, timeout=30, **kwargs
        )
        if not response.ok:
            raise SystemExit(f"{method} {url} -> {response.status_code}: {response.text[:500]}")
        return response

    def _paged(self, url: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor = None
        while True:
            params = {"cursor": cursor} if cursor else {}
            body = self._request("GET", url, params=params).json()
            results.extend(body.get("result", []))
            cursor = body.get("paging_metadata", {}).get("cursor")
            if not cursor:
                break
        return results

    # ---- individual entities (shells / submodels / concept-descriptions) ----
    def list_entities(self, entity_type: str) -> list[dict[str, Any]]:
        return self._paged(f"{self.server.url.rstrip('/')}/{ENTITY_PATHS[entity_type]}")

    def get_entity(self, entity_type: str, identifier: str) -> dict[str, Any]:
        url = f"{self.server.url.rstrip('/')}/{ENTITY_PATHS[entity_type]}/{encode_id(identifier)}"
        return self._request("GET", url).json()

    def create_entity(self, entity_type: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.server.url.rstrip('/')}/{ENTITY_PATHS[entity_type]}"
        return self._request("POST", url, json=body).json()

    def delete_entity(self, entity_type: str, identifier: str) -> None:
        url = f"{self.server.url.rstrip('/')}/{ENTITY_PATHS[entity_type]}/{encode_id(identifier)}"
        self._request("DELETE", url)

    # ---- bulk environment files (AASX / JSON / XML) --------------------------
    def upload_environment(self, file_path: Path, ignore_duplicates: bool = False) -> None:
        url = f"{self.server.url.rstrip('/')}/upload"
        params = {"ignore-duplicates": str(ignore_duplicates).lower()}
        content_type = UPLOAD_CONTENT_TYPE_BY_SUFFIX.get(
            file_path.suffix.lower(), "application/octet-stream"
        )
        with file_path.open("rb") as fh:
            self._request(
                "POST", url, params=params, files={"file": (file_path.name, fh, content_type)}
            )

    def download_serialization(
        self,
        aas_ids: Iterable[str] = (),
        submodel_ids: Iterable[str] = (),
        include_concept_descriptions: bool = True,
        fmt: str = "json",
    ) -> bytes:
        aas_ids = list(aas_ids)
        submodel_ids = list(submodel_ids)
        if not aas_ids and not submodel_ids:
            # /serialization with neither id list set throws a bare 400 on
            # this BaSyx build -- list everything and pass ids explicitly.
            aas_ids = [e["id"] for e in self.list_entities("shell")]
            submodel_ids = [e["id"] for e in self.list_entities("submodel")]

        url = f"{self.server.url.rstrip('/')}/serialization"
        params = {
            "aasIds": [encode_id(i) for i in aas_ids],
            "submodelIds": [encode_id(i) for i in submodel_ids],
            "includeConceptDescriptions": str(include_concept_descriptions).lower(),
        }
        headers = {"Accept": ACCEPT_BY_FORMAT[fmt]}
        return self._request("GET", url, params=params, headers=headers).content

    # ---- registry (shell-/submodel-descriptors, if server.registry_url set) --
    def list_registry(self, entity_type: str) -> list[dict[str, Any]]:
        if not self.server.registry_url:
            raise SystemExit(f"Server '{self.server.name}' has no registry_url configured")
        descriptor_path = "shell-descriptors" if entity_type == "shell" else "submodel-descriptors"
        return self._paged(f"{self.server.registry_url.rstrip('/')}/{descriptor_path}")
