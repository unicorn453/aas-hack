#!/usr/bin/env python3
"""
Discover remote shell offers through EDC catalog only.

This script does not register shell descriptors in a partner registry.
It asks your local EDC control plane to query a remote partner catalog,
then prints catalog datasets that look like AAS shell endpoints.

Examples:
  python3 tools/search_shells_via_edc.py --provider-url https://192.168.56.20
  python3 tools/search_shells_via_edc.py --provider-url https://192.168.56.20 --raw
"""

import argparse
import json
import os
from urllib.parse import urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _candidate_catalog_endpoints(management_url: str) -> list[str]:
    """Return likely catalog request endpoints for different EDC API layouts."""
    base = management_url.rstrip("/")
    candidates = [
        f"{base}/v3/catalog/request",
        f"{base}/catalog/request",
    ]

    # If caller passed /api/management, also try /management variants.
    if base.endswith("/api/management"):
        root = base[: -len("/api/management")]
        candidates.extend(
            [
                f"{root}/management/v3/catalog/request",
                f"{root}/management/catalog/request",
                f"{root}/v3/catalog/request",
                f"{root}/catalog/request",
            ]
        )

    # If caller passed /management, also try /api/management variants.
    if base.endswith("/management") and not base.endswith("/api/management"):
        root = base[: -len("/management")]
        candidates.extend(
            [
                f"{root}/api/management/v3/catalog/request",
                f"{root}/api/management/catalog/request",
                f"{root}/v3/catalog/request",
                f"{root}/catalog/request",
            ]
        )

    # Some users pass the host root instead of /api/management.
    if not base.endswith("/api/management") and not base.endswith("/management"):
        candidates.extend(
            [
                f"{base}/api/management/v3/catalog/request",
                f"{base}/api/management/catalog/request",
                f"{base}/management/v3/catalog/request",
                f"{base}/management/catalog/request",
            ]
        )

    # Keep order stable while deduplicating.
    seen = set()
    unique = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _post_catalog_request(endpoints: list[str], headers: dict, payload: dict):
    """Try known endpoint variants until one succeeds or all fail."""
    last_response = None
    last_endpoint = None
    errors = []
    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30, verify=False)
        except requests.RequestException as exc:
            errors.append((endpoint, f"{exc.__class__.__name__}: {exc}"))
            continue

        last_response = response
        last_endpoint = endpoint
        if response.status_code < 400:
            return endpoint, response, errors

        # 404/405 usually means wrong path on this deployment; try next candidate.
        if response.status_code in (404, 405):
            continue

        # For auth or server errors, return immediately to preserve useful diagnostics.
        return endpoint, response, errors

    return last_endpoint, last_response, errors


def _provider_host(provider_url: str) -> str:
    parsed = urlparse(provider_url)
    if not parsed.hostname:
        raise ValueError(f"Invalid provider URL: {provider_url}")
    return parsed.hostname


def _provider_dsp_url(provider_url: str) -> str:
    parsed = urlparse(provider_url)
    if not parsed.hostname:
        raise ValueError(f"Invalid provider URL: {provider_url}")
    # In this stack the DSP endpoint runs on the connector's HTTP context on 19191.
    return f"http://{parsed.hostname}:19191/api/dsp"


def _provider_participant_id(provider_url: str) -> str:
    return f"did:web:{_provider_host(provider_url)}"


def _collect_dataset_nodes(node):
    datasets = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_l = str(key).lower()
            if "dataset" in key_l:
                if isinstance(value, list):
                    datasets.extend([v for v in value if isinstance(v, dict)])
                elif isinstance(value, dict):
                    datasets.append(value)
            datasets.extend(_collect_dataset_nodes(value))
    elif isinstance(node, list):
        for item in node:
            datasets.extend(_collect_dataset_nodes(item))
    return datasets


def _dataset_id(dataset: dict) -> str:
    return str(dataset.get("@id") or dataset.get("id") or "<no-id>")


def _looks_like_shell_dataset(dataset: dict) -> bool:
    text = json.dumps(dataset, ensure_ascii=True).lower()
    return "shell" in text or "/shells" in text


def _summary_line(dataset: dict) -> str:
    raw = json.dumps(dataset, ensure_ascii=True)
    compact = " ".join(raw.split())
    return compact[:220] + ("..." if len(compact) > 220 else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-url", required=True, help="Partner base URL, e.g. https://192.168.56.20")
    parser.add_argument(
        "--management-url",
        default="http://localhost:19193/api/management",
        help="Local EDC management base URL (default: http://localhost:19193/api/management)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("EDC_API_KEY", "password"),
        help="Local EDC management API key (default: EDC_API_KEY env or 'password')",
    )
    parser.add_argument(
        "--provider-dsp-url",
        default=None,
        help="Remote DSP endpoint override (default: <provider-host>:19191/api/dsp)",
    )
    parser.add_argument(
        "--provider-participant-id",
        default=None,
        help="Remote participant id override (default: did:web:<provider-host>)",
    )
    parser.add_argument("--limit", type=int, default=50, help="Catalog query page size")
    parser.add_argument("--raw", action="store_true", help="Print raw catalog response JSON")
    args = parser.parse_args()

    provider_dsp_url = args.provider_dsp_url or _provider_dsp_url(args.provider_url)
    provider_participant_id = args.provider_participant_id or _provider_participant_id(args.provider_url)

    payload = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@type": "CatalogRequest",
        "counterPartyAddress": provider_dsp_url,
        "counterPartyId": provider_participant_id,
        "protocol": "dataspace-protocol-http",
        "querySpec": {
            "@type": "QuerySpec",
            "offset": 0,
            "limit": args.limit,
        },
    }

    endpoints = _candidate_catalog_endpoints(args.management_url)
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": args.api_key,
    }

    endpoint, response, errors = _post_catalog_request(endpoints, headers, payload)
    if response is None:
        print("Catalog request failed: no reachable management endpoint candidates")
        print("Tried:")
        for candidate in endpoints:
            print(f"  - {candidate}")
        if errors:
            print("Connection errors:")
            for failing_endpoint, message in errors:
                print(f"  - {failing_endpoint} -> {message}")
        return 1

    if response.status_code >= 400:
        print(f"Catalog request failed at {endpoint}: HTTP {response.status_code}")
        print(response.text)
        return 1

    print(f"Catalog request succeeded via {endpoint}")

    catalog = response.json()
    if args.raw:
        print(json.dumps(catalog, indent=2, ensure_ascii=True))

    datasets = _collect_dataset_nodes(catalog)
    if not datasets:
        print("No datasets found in remote catalog response.")
        return 0

    shell_datasets = [d for d in datasets if _looks_like_shell_dataset(d)]
    print(f"Found {len(datasets)} dataset(s) in remote catalog.")
    print(f"Shell-like dataset(s): {len(shell_datasets)}")

    if not shell_datasets:
        print("No shell-like offers found. Use --raw to inspect full catalog.")
        return 0

    for idx, dataset in enumerate(shell_datasets, start=1):
        print(f"\n[{idx}] id={_dataset_id(dataset)}")
        print(_summary_line(dataset))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
