#!/usr/bin/env python3
import argparse
import base64
import json
from pathlib import Path
from typing import Iterable

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_token(
    token_url: str,
    client_id: str,
    username: str,
    password: str,
    client_secret: str | None,
    verify: bool,
) -> str:
    token_url = token_url.rstrip("/")
    candidates = [token_url]
    if "/auth/realms/" not in token_url and "/realms/" in token_url:
        candidates.append(token_url.replace("/realms/", "/auth/realms/", 1))

    data = {
        "client_id": client_id,
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    if client_secret:
        data["client_secret"] = client_secret

    last_error = None
    for candidate in candidates:
        response = requests.post(candidate, data=data, timeout=30, verify=verify)
        if response.status_code == 404:
            last_error = f"{response.status_code} at {candidate}"
            continue

        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"No access_token in token response from {candidate}: {payload}")
        return token

    raise RuntimeError(f"Token endpoint not found. Tried: {', '.join(candidates)}. Last error: {last_error}")


def b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def iter_env_files(root: Path) -> Iterable[Path]:
    return sorted(root.rglob("environment.json"))


def upsert(session: requests.Session, collection_url: str, item_url: str, payload: dict, label: str) -> str:
    r = session.post(collection_url, json=payload, timeout=30)
    if r.status_code in (200, 201, 204):
        return f"created {label}"
    if r.status_code == 409:
        r2 = session.put(item_url, json=payload, timeout=30)
        if r2.status_code in (200, 201, 204):
            return f"updated {label}"
        return f"failed-update {label}: {r2.status_code} {r2.text[:200]}"
    return f"failed-create {label}: {r.status_code} {r.text[:200]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk upload AAS environments from environment.json files")
    parser.add_argument(
        "--root",
        default="converters/excel-to-aasx/data/generated/schunk/xlsx-json-step4",
        help="Root folder to scan for environment.json",
    )
    parser.add_argument(
        "--base-url",
        default="https://127.0.0.1",
        help="AAS API base URL, e.g. https://172.17.255.170",
    )
    parser.add_argument("--token", default=None, help="Optional Bearer token")
    parser.add_argument(
        "--token-url",
        default=None,
        help="Keycloak token endpoint, e.g. http://172.17.255.170:8084/realms/basyx/protocol/openid-connect/token",
    )
    parser.add_argument("--username", default="basyx-admin", help="Keycloak username for token fetch")
    parser.add_argument("--password", default="basyx-admin", help="Keycloak password for token fetch")
    parser.add_argument("--client-id", default="basyx-web", help="Keycloak client_id for token fetch")
    parser.add_argument("--client-secret", default=None, help="Optional Keycloak client secret")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification")
    parser.add_argument("--dry-run", action="store_true", help="Only show what would be uploaded")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root does not exist: {root}")
        return 1

    files = list(iter_env_files(root))
    if not files:
        print(f"No environment.json files found under: {root}")
        return 1

    session = requests.Session()
    session.verify = not args.insecure
    session.headers.update({"Content-Type": "application/json"})

    token = args.token
    if not token and args.token_url:
        token = fetch_token(
            token_url=args.token_url,
            client_id=args.client_id,
            username=args.username,
            password=args.password,
            client_secret=args.client_secret,
            verify=not args.insecure,
        )
        print("Fetched access token from Keycloak")

    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    total_created_or_updated = 0
    total_failed = 0

    for env_file in files:
        print(f"\n== Processing {env_file} ==")
        data = json.loads(env_file.read_text(encoding="utf-8"))

        shells = data.get("assetAdministrationShells", [])
        submodels = data.get("submodels", [])
        concept_descriptions = data.get("conceptDescriptions", [])

        if args.dry_run:
            print(f"Would upload: shells={len(shells)} submodels={len(submodels)} conceptDescriptions={len(concept_descriptions)}")
            continue

        # shells
        for shell in shells:
            shell_id = shell.get("id")
            if not shell_id:
                total_failed += 1
                print("failed shell with missing id")
                continue
            collection = f"{args.base_url.rstrip('/')}/shells"
            item = f"{args.base_url.rstrip('/')}/shells/{b64url(shell_id)}"
            msg = upsert(session, collection, item, shell, f"shell {shell_id}")
            print(msg)
            if msg.startswith(("created", "updated")):
                total_created_or_updated += 1
            else:
                total_failed += 1

        # submodels
        for sm in submodels:
            sm_id = sm.get("id")
            if not sm_id:
                total_failed += 1
                print("failed submodel with missing id")
                continue
            collection = f"{args.base_url.rstrip('/')}/submodels"
            item = f"{args.base_url.rstrip('/')}/submodels/{b64url(sm_id)}"
            msg = upsert(session, collection, item, sm, f"submodel {sm_id}")
            print(msg)
            if msg.startswith(("created", "updated")):
                total_created_or_updated += 1
            else:
                total_failed += 1

        # concept descriptions
        for cd in concept_descriptions:
            cd_id = cd.get("id")
            if not cd_id:
                total_failed += 1
                print("failed conceptDescription with missing id")
                continue
            collection = f"{args.base_url.rstrip('/')}/concept-descriptions"
            item = f"{args.base_url.rstrip('/')}/concept-descriptions/{b64url(cd_id)}"
            msg = upsert(session, collection, item, cd, f"conceptDescription {cd_id}")
            print(msg)
            if msg.startswith(("created", "updated")):
                total_created_or_updated += 1
            else:
                total_failed += 1

    print("\n== Done ==")
    print(f"successful create/update: {total_created_or_updated}")
    print(f"failed: {total_failed}")
    return 0 if total_failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())