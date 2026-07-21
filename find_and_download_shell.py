"""
Shell über die AAS Registry finden und herunterladen — mit dem Open-Source-
Client "aas-python-http-client" (generiert aus der offiziellen IDTA
AAS-API-v3-Spezifikation, Modelle aus dem BaSyx Python SDK).

Ablauf:
  1. Token von Keycloak holen (Password Grant)
  2. Registry: alle Shell Descriptors auflisten
  3. Descriptor der gesuchten Shell holen
  4. Endpoint-URL aus dem Descriptor auflösen (endpoints[0].protocolInformation.href)
  5. Shell direkt vom Endpoint herunterladen und als JSON speichern

Setup (einmalig):
    .venv-scripts/bin/pip install aas-python-http-client

Ausführen:
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

# Selbstsignierte Zertifikate -> Warnungen unterdrücken
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_token(keycloak_url: str, realm: str, client_id: str,
              client_secret: str, username: str, password: str) -> str:
    """Access Token von Keycloak per Password Grant holen."""
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
    """Registry-API-Client mit Bearer-Token konfigurieren."""
    config = Configuration()
    config.host = registry_url
    config.verify_ssl = False  # selbstsignierte Zertifikate im Hackathon-Setup
    client = ApiClient(configuration=config)
    client.set_default_header("Authorization", f"Bearer {token}")
    return AssetAdministrationShellRegistryAPIApi(api_client=client)


def resolve_endpoint(descriptor) -> str:
    """Endpoint-URL (href) aus einem Shell Descriptor lesen."""
    if not descriptor.endpoints:
        raise ValueError(f"Descriptor {descriptor.id!r} enthält keine Endpoints")
    return descriptor.endpoints[0].protocol_information.href


def download_shell(endpoint_href: str, token: str) -> dict:
    """Shell direkt von der im Descriptor hinterlegten Endpoint-URL laden."""
    response = requests.get(
        endpoint_href,
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def save_json(data: dict, aas_id: str, out_dir: str = "downloaded_shells") -> Path:
    """Shell als JSON speichern; Dateiname aus der AAS-ID ableiten."""
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
                        help="AAS-ID der gesuchten Shell (Standard: erste registrierte Shell)")
    args = parser.parse_args()

    # 1) Authentifizieren
    token = get_token(args.keycloak_url, args.realm, args.client_id,
                      args.client_secret, args.username, args.password)
    print(f"[auth] Token erhalten ({len(token)} Zeichen)")

    registry = make_registry_client(args.registry_url, token)

    # 2) Alle Shell Descriptors auflisten (Antwort ist paginiert -> .result)
    page = registry.get_all_asset_administration_shell_descriptors()
    descriptors = page.result or []
    print(f"[registry] {len(descriptors)} Shell(s) registriert:")
    for d in descriptors:
        print(f"           {d.id} -> {resolve_endpoint(d)}")

    if not descriptors:
        print("Nichts registriert — erst eine Shell hochladen, dann erneut ausführen.")
        return

    # 3) Descriptor der gesuchten Shell holen
    #    Achtung: Die ID muss selbst Base64-URL-kodiert werden — der Client
    #    macht das nicht automatisch (er würde die ID nur URL-encodieren,
    #    was der Server mit 400 ablehnt).
    aas_id = args.aas_id or descriptors[0].id
    descriptor = registry.get_asset_administration_shell_descriptor_by_id(
        string_to_base64url(aas_id)
    )

    # 4) Endpoint auflösen
    href = resolve_endpoint(descriptor)
    print(f"[resolve] {aas_id} -> {href}")

    # 5) Shell herunterladen und speichern
    shell = download_shell(href, token)
    path = save_json(shell, aas_id)
    print(f"[download] Shell {shell.get('idShort', aas_id)!r} gespeichert: {path}")


if __name__ == "__main__":
    main()
