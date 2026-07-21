"""
Find a shell via the AAS registry and download it — using the open-source
client "aas-python-http-client" (generated from the official IDTA AAS API
v3 specification, models from the BaSyx Python SDK).

Flow:
  1. Get a token from Keycloak (password grant)
  2. Registry: list all shell descriptors
  3. Fetch the descriptor of the requested shell
  4. Resolve the endpoint URL from the descriptor
     (endpoints[0].protocolInformation.href)
  5. Download the shell directly from the endpoint and save it as JSON

Note: this script talks to ONE stack with one token. For multi-host setups
(cross-registered descriptors) see aas_client.py / SCRIPTS.md.

Setup (once):
    .venv-scripts/bin/pip install aas-python-http-client

Run:
    .venv-scripts/bin/python3 find_and_download_shell.py
    .venv-scripts/bin/python3 find_and_download_shell.py --aas-id https://acplt.org/Simple_AAS
    .venv-scripts/bin/python3 find_and_download_shell.py --registry-url https://<partner-ip> --keycloak-url https://<partner-ip>/auth
"""

import argparse
import json
import re
from pathlib import Path

import requests
import urllib3

from aas_python_http_client import ApiClient, Configuration
from aas_python_http_client.api.asset_administration_shell_registry_api_api import (
    AssetAdministrationShellRegistryAPIApi,
)
from aas_python_http_client.util import string_to_base64url

# Self-signed certificates -> suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_token(keycloak_url: str, realm: str, client_id: str,
              client_secret: str, username: str, password: str) -> str:
    """Get an access token from Keycloak via password grant."""
    response = requests.post(
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        verify=False,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def make_registry_client(registry_url: str, token: str) -> AssetAdministrationShellRegistryAPIApi:
    """Configure a registry API client with a bearer token."""
    config = Configuration()
    config.host = registry_url
    config.verify_ssl = False  # self-signed certificates in the hackathon setup
    client = ApiClient(configuration=config)
    client.set_default_header("Authorization", f"Bearer {token}")
    return AssetAdministrationShellRegistryAPIApi(api_client=client)


def resolve_endpoint(descriptor) -> str:
    """Read the endpoint URL (href) from a shell descriptor."""
    if not descriptor.endpoints:
        raise ValueError(f"Descriptor {descriptor.id!r} contains no endpoints")
    return descriptor.endpoints[0].protocol_information.href


def download_shell(endpoint_href: str, token: str) -> dict:
    """Load a shell directly from the endpoint URL stored in its descriptor."""
    response = requests.get(
        endpoint_href,
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def save_json(data: dict, aas_id: str, out_dir: str = "downloaded_shells") -> Path:
    """Save a shell as JSON; derive the file name from the AAS id."""
    Path(out_dir).mkdir(exist_ok=True)
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", aas_id) + ".json"
    path = Path(out_dir) / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry-url", default="https://192.168.56.76")
    parser.add_argument("--keycloak-url", default="https://192.168.56.76/auth")
    parser.add_argument("--realm", default="basyx")
    parser.add_argument("--client-id", default="basyx-api")
    parser.add_argument("--client-secret", default="basyx-api-secret")
    parser.add_argument("--username", default="basyx-admin")
    parser.add_argument("--password", default="basyx-admin")
    parser.add_argument("--aas-id", default=None,
                        help="AAS id of the requested shell (default: first registered shell)")
    args = parser.parse_args()

    # 1) Authenticate
    token = get_token(args.keycloak_url, args.realm, args.client_id,
                      args.client_secret, args.username, args.password)
    print(f"[auth] got token ({len(token)} chars)")

    registry = make_registry_client(args.registry_url, token)

    # 2) List all shell descriptors (paginated response -> .result)
    page = registry.get_all_asset_administration_shell_descriptors()
    descriptors = page.result or []
    print(f"[registry] {len(descriptors)} shell(s) registered:")
    for d in descriptors:
        print(f"           {d.id} -> {resolve_endpoint(d)}")

    if not descriptors:
        print("Nothing registered — upload a shell first, then rerun.")
        return

    # 3) Fetch the descriptor of the requested shell
    #    Note: the id must be base64url-encoded by us — the client does not
    #    do that automatically (it would only URL-encode the id, which the
    #    server rejects with 400).
    aas_id = args.aas_id or descriptors[0].id
    descriptor = registry.get_asset_administration_shell_descriptor_by_id(
        string_to_base64url(aas_id)
    )

    # 4) Resolve the endpoint
    href = resolve_endpoint(descriptor)
    print(f"[resolve] {aas_id} -> {href}")

    # 5) Download the shell and save it
    shell = download_shell(href, token)
    path = save_json(shell, aas_id)
    print(f"[download] shell {shell.get('idShort', aas_id)!r} saved: {path}")


if __name__ == "__main__":
    main()
