import argparse
import json
from pathlib import Path

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_token(keycloak_url, realm, client_id, client_secret, username, password):
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


def list_shell_descriptors(registry_url, token):
    response = requests.get(
        f"{registry_url}/shell-descriptors",
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("result", data) if isinstance(data, dict) else data


def download_shell(href, token):
    response = requests.get(
        href,
        headers={"Authorization": f"Bearer {token}"},
        verify=False,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Download AAS shells from the registry")
    parser.add_argument("--registry-url", default="https://172.17.255.202", help="Base URL of the registry")
    parser.add_argument("--keycloak-url", default="https://172.17.255.202/auth", help="Base URL of Keycloak")
    parser.add_argument("--realm", default="basyx")
    parser.add_argument("--client-id", default="basyx-api")
    parser.add_argument("--client-secret", default="basyx-api-secret")
    parser.add_argument("--username", default="basyx-admin")
    parser.add_argument("--password", default="basyx-admin")
    parser.add_argument("--aas-id", default=None, help="Only download this exact AAS id")
    parser.add_argument("--out-dir", default="downloaded_shells")
    args = parser.parse_args()

    token = get_token(
        args.keycloak_url,
        args.realm,
        args.client_id,
        args.client_secret,
        args.username,
        args.password,
    )

    descriptors = list_shell_descriptors(args.registry_url, token)
    if args.aas_id:
        descriptors = [descriptor for descriptor in descriptors if descriptor["id"] == args.aas_id]
        if not descriptors:
            raise SystemExit(f"No shell descriptor found for id {args.aas_id!r}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)

    for descriptor in descriptors:
        aas_id = descriptor["id"]
        href = descriptor["endpoints"][0]["protocolInformation"]["href"]
        shell = download_shell(href, token)

        safe_name = "".join(char if char.isalnum() else "_" for char in aas_id).strip("_")
        out_path = out_dir / f"{safe_name}.json"
        out_path.write_text(json.dumps(shell, indent=2))
        print(f"Downloaded {aas_id} -> {out_path}")


if __name__ == "__main__":
    main()