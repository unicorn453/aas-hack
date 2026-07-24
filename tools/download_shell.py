"""
Downloads Asset Administration Shells from a BaSyx AAS Registry.

The registry only stores *descriptors* (id, asset info, and an endpoint URL) -
not the shell data itself. This script queries the registry to find where a
shell actually lives, then fetches it from that endpoint. Since the endpoint
in the descriptor can point at any reachable AAS server, the same script works
against a remote/partner registry by just changing --registry-url.

Usage:
    pip install requests
    python3 tools/download_shell.py
    python3 tools/download_shell.py --aas-id "https://acplt.org/Simple_AAS"
    python3 tools/download_shell.py --registry-url https://<partner-ip>
examlple:
    .venv-scripts/bin/python3 tools/download_shell.py
    .venv-scripts/bin/python3 tools/download_shell.py --aas-id "https://acplt.org/Simple_AAS"
    .venv-scripts/bin/python3 tools/download_shell.py --registry-url https://<example-ip> --keycloak-url https://<example-ip>/auth


"""

import argparse
import json
from pathlib import Path

import requests
import urllib3


def get_token(keycloak_url, realm, client_id, client_secret, username, password, verify):
    resp = requests.post(
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        verify=verify,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def list_shell_descriptors(registry_url, token, verify):
    resp = requests.get(
        f"{registry_url}/shell-descriptors",
        headers={"Authorization": f"Bearer {token}"},
        verify=verify,
    )
    resp.raise_for_status()
    return resp.json()["result"]


def download_shell(href, token, verify):
    resp = requests.get(href, headers={"Authorization": f"Bearer {token}"}, verify=verify)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry-url", default="https://192.168.56.76", help="Base URL of the AAS registry")
    parser.add_argument("--keycloak-url", default="https://192.168.56.76/auth", help="Base URL of Keycloak")
    parser.add_argument("--realm", default="basyx")
    parser.add_argument("--client-id", default="basyx-api")
    parser.add_argument("--client-secret", default="basyx-api-secret")
    parser.add_argument("--username", default="basyx-admin")
    parser.add_argument("--password", default="basyx-admin")
    parser.add_argument("--aas-id", default=None, help="Only download the shell with this exact AAS id (default: all)")
    parser.add_argument("--out-dir", default="downloaded_shells")
    parser.add_argument("--insecure", action="store_true", default=True,
                         help="Skip TLS verification (default: on, since these stacks use self-signed certs)")
    args = parser.parse_args()
    verify = not args.insecure
    if not verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    token = get_token(args.keycloak_url, args.realm, args.client_id, args.client_secret,
                       args.username, args.password, verify)

    descriptors = list_shell_descriptors(args.registry_url, token, verify)
    if args.aas_id:
        descriptors = [d for d in descriptors if d["id"] == args.aas_id]
        if not descriptors:
            raise SystemExit(f"No shell descriptor found for id {args.aas_id!r}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)

    for descriptor in descriptors:
        aas_id = descriptor["id"]
        href = descriptor["endpoints"][0]["protocolInformation"]["href"]
        print(f"Downloading {aas_id} from {href}")

        shell = download_shell(href, token, verify)

        safe_name = "".join(c if c.isalnum() else "_" for c in aas_id).strip("_")
        out_path = out_dir / f"{safe_name}.json"
        out_path.write_text(json.dumps(shell, indent=2))
        print(f"  -> saved to {out_path}")


if __name__ == "__main__":
    main()
