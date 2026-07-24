"""
Cross-registration: register your own shells in a partner's registry so
the partner finds them in their own registry and reads the data LIVE from
our server (no copy needed).

How it works:
  - Reads your own shell descriptors from YOUR registry (aas-env puts them
    there automatically via registryintegration; the endpoint hrefs point at
    your external address via basyx.externalurl).
  - Pushes those descriptors 1:1 to the PARTNER's AAS registry.
  - Also pushes each shell's submodel descriptors to the partner's submodel
    registry.
  - --deregister removes all previously pushed entries from the partner
    (use before shutting down your stack).

Prerequisites:
  - The partner can reach your IP (same LAN / VPN).
  - You have credentials for the partner's Keycloak with write access to
    their registry (ask them for an account, or use basyx-admin for hackathon).
  - Your own RBAC rules allow the partner to read shells/submodels.

Usage:
    pip install requests

    # Register all your shells at the partner
    python3 tools/register_remote.py --partner-url https://<partner-ip>

    # Register only one specific shell
    python3 tools/register_remote.py --partner-url https://<partner-ip> --aas-id <aas-id>

    # Remove your shells from the partner registry again
    python3 tools/register_remote.py --partner-url https://<partner-ip> --deregister

Example (hackathon defaults — replace IPs):
    python3 tools/register_remote.py \\
        --my-url https://192.168.56.10 \\
        --partner-url https://192.168.56.20 \\
        --partner-username basyx-admin --partner-password basyx-admin
"""

import argparse
import base64
import json
import os
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 10


def _default_my_url() -> str:
    host_address = os.getenv("HOST_ADDRESS")
    if host_address:
        return f"https://{host_address}"

    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("HOST_ADDRESS="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return f"https://{value}"

    return "https://127.0.0.1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64(value: str) -> str:
    """URL-safe base64 encoding without padding (used by BaSyx for ids in URLs)."""
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def get_token(keycloak_url, realm, client_id, client_secret, username, password):
    resp = requests.post(
        f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        verify=False,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Registry operations
# ---------------------------------------------------------------------------

def list_shell_descriptors(registry_url, token):
    resp = requests.get(
        f"{registry_url}/shell-descriptors",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", data) if isinstance(data, dict) else data


def get_shell_descriptor(registry_url, token, aas_id):
    resp = requests.get(
        f"{registry_url}/shell-descriptors/{_b64(aas_id)}",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def upsert_shell_descriptor(registry_url, token, descriptor):
    aas_id = descriptor["id"]
    # Try PUT first (update), fall back to POST (create)
    put = requests.put(
        f"{registry_url}/shell-descriptors/{_b64(aas_id)}",
        headers=auth_headers(token),
        json=descriptor,
        verify=False,
        timeout=TIMEOUT,
    )
    if put.status_code == 404:
        post = requests.post(
            f"{registry_url}/shell-descriptors",
            headers=auth_headers(token),
            json=descriptor,
            verify=False,
            timeout=TIMEOUT,
        )
        post.raise_for_status()
        return "created"
    put.raise_for_status()
    return "updated"


def delete_shell_descriptor(registry_url, token, aas_id):
    resp = requests.delete(
        f"{registry_url}/shell-descriptors/{_b64(aas_id)}",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    if resp.status_code == 404:
        return "not found"
    resp.raise_for_status()
    return "deleted"


def list_submodel_descriptors(sm_registry_url, token):
    resp = requests.get(
        f"{sm_registry_url}/submodel-descriptors",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", data) if isinstance(data, dict) else data


def get_submodel_descriptor(sm_registry_url, token, sm_id):
    resp = requests.get(
        f"{sm_registry_url}/submodel-descriptors/{_b64(sm_id)}",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def upsert_submodel_descriptor(sm_registry_url, token, descriptor):
    sm_id = descriptor["id"]
    put = requests.put(
        f"{sm_registry_url}/submodel-descriptors/{_b64(sm_id)}",
        headers=auth_headers(token),
        json=descriptor,
        verify=False,
        timeout=TIMEOUT,
    )
    if put.status_code == 404:
        post = requests.post(
            f"{sm_registry_url}/submodel-descriptors",
            headers=auth_headers(token),
            json=descriptor,
            verify=False,
            timeout=TIMEOUT,
        )
        post.raise_for_status()
        return "created"
    put.raise_for_status()
    return "updated"


def delete_submodel_descriptor(sm_registry_url, token, sm_id):
    resp = requests.delete(
        f"{sm_registry_url}/submodel-descriptors/{_b64(sm_id)}",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    if resp.status_code == 404:
        return "not found"
    resp.raise_for_status()
    return "deleted"


# ---------------------------------------------------------------------------
# Shell repository — needed to discover which submodel ids belong to a shell
# ---------------------------------------------------------------------------

def download_shell(aas_env_url, token, aas_id):
    resp = requests.get(
        f"{aas_env_url}/shells/{_b64(aas_id)}",
        headers=auth_headers(token),
        verify=False,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def submodel_ids_of(shell: dict) -> list:
    return [ref["keys"][0]["value"]
            for ref in shell.get("submodels", [])
            if ref.get("keys")]


# ---------------------------------------------------------------------------
# High-level actions
# ---------------------------------------------------------------------------

def own_shell_ids(my_registry_url, my_token, my_url):
    """Return ids of shells whose endpoint points at our own server (filter out foreign cross-registrations)."""
    ids = []
    for descriptor in list_shell_descriptors(my_registry_url, my_token):
        try:
            href = descriptor["endpoints"][0]["protocolInformation"]["href"]
        except (KeyError, IndexError):
            continue
        if href.startswith(my_url):
            ids.append(descriptor["id"])
    return ids


def register_one(
    my_registry_url, my_token,
    my_sm_registry_url,
    my_aas_env_url,
    partner_registry_url, partner_token,
    partner_sm_registry_url,
    aas_id,
):
    descriptor = get_shell_descriptor(my_registry_url, my_token, aas_id)
    status = upsert_shell_descriptor(partner_registry_url, partner_token, descriptor)
    print(f"  [shell-descriptor] {descriptor.get('idShort', aas_id)!r}: {status}")

    # Discover submodels from our own repository
    try:
        shell = download_shell(my_aas_env_url, my_token, aas_id)
        sm_ids = submodel_ids_of(shell)
    except requests.HTTPError as exc:
        print(f"  [warning] could not download shell from env to get submodel ids: {exc}")
        sm_ids = []

    for sm_id in sm_ids:
        try:
            sm_descriptor = get_submodel_descriptor(my_sm_registry_url, my_token, sm_id)
        except requests.HTTPError:
            print(f"  [submodel-descriptor] {sm_id!r}: not in own registry, skipped")
            continue
        status = upsert_submodel_descriptor(partner_sm_registry_url, partner_token, sm_descriptor)
        print(f"  [submodel-descriptor] {sm_descriptor.get('idShort', sm_id)!r}: {status}")


def deregister_one(
    my_registry_url, my_token,
    my_sm_registry_url,
    my_aas_env_url,
    partner_registry_url, partner_token,
    partner_sm_registry_url,
    aas_id,
):
    # Collect submodel ids while we still have the shell
    try:
        shell = download_shell(my_aas_env_url, my_token, aas_id)
        sm_ids = submodel_ids_of(shell)
    except requests.HTTPError:
        sm_ids = []

    status = delete_shell_descriptor(partner_registry_url, partner_token, aas_id)
    print(f"  [shell-descriptor] {aas_id!r}: {status}")

    for sm_id in sm_ids:
        status = delete_submodel_descriptor(partner_sm_registry_url, partner_token, sm_id)
        print(f"  [submodel-descriptor] {sm_id!r}: {status}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # --- own stack ---
    parser.add_argument("--my-url", default=_default_my_url(),
                        help="Base URL of YOUR stack (used to filter own shells and reach your env/registries)")
    parser.add_argument("--my-keycloak-url", default=None,
                        help="Keycloak URL for YOUR stack (default: <my-url>/auth)")
    parser.add_argument("--my-realm", default="basyx")
    parser.add_argument("--my-client-id", default="basyx-api")
    parser.add_argument("--my-client-secret", default="basyx-api-secret")
    parser.add_argument("--my-username", default="basyx-admin")
    parser.add_argument("--my-password", default="basyx-admin")

    # --- partner stack ---
    parser.add_argument("--partner-url", required=True,
                        help="Base URL of the PARTNER stack")
    parser.add_argument("--partner-keycloak-url", default=None,
                        help="Keycloak URL for the PARTNER stack (default: <partner-url>/auth)")
    parser.add_argument("--partner-realm", default="basyx")
    parser.add_argument("--partner-client-id", default="basyx-api")
    parser.add_argument("--partner-client-secret", default="basyx-api-secret")
    parser.add_argument("--partner-username", default="basyx-admin")
    parser.add_argument("--partner-password", default="basyx-admin")

    # --- target shell ---
    parser.add_argument("--aas-id", default=None,
                        help="Only register/deregister this specific AAS id (default: all own shells)")
    parser.add_argument("--deregister", action="store_true",
                        help="Remove shells from partner registry instead of adding them")

    args = parser.parse_args()

    my_url = args.my_url.rstrip("/")
    partner_url = args.partner_url.rstrip("/")
    my_keycloak_url = (args.my_keycloak_url or f"{my_url}/auth").rstrip("/")
    partner_keycloak_url = (args.partner_keycloak_url or f"{partner_url}/auth").rstrip("/")

    # Registry functions append their own paths (/shell-descriptors, /shells, etc.)
    my_registry_url      = my_url
    my_sm_registry_url   = my_url
    my_aas_env_url       = my_url
    partner_registry_url = partner_url
    partner_sm_registry_url = partner_url

    print(f"Authenticating against own Keycloak  ({my_keycloak_url}) …")
    my_token = get_token(my_keycloak_url, args.my_realm, args.my_client_id,
                         args.my_client_secret, args.my_username, args.my_password)

    print(f"Authenticating against partner Keycloak ({partner_keycloak_url}) …")
    partner_token = get_token(partner_keycloak_url, args.partner_realm,
                              args.partner_client_id, args.partner_client_secret,
                              args.partner_username, args.partner_password)

    if args.aas_id:
        aas_ids = [args.aas_id]
    else:
        print("Listing own shells …")
        aas_ids = own_shell_ids(my_registry_url, my_token, my_url)
        print(f"Found {len(aas_ids)} own shell(s).")

    action = "Deregistering" if args.deregister else "Registering"
    for aas_id in aas_ids:
        print(f"\n{action}: {aas_id}")
        if args.deregister:
            deregister_one(
                my_registry_url, my_token,
                my_sm_registry_url, my_aas_env_url,
                partner_registry_url, partner_token,
                partner_sm_registry_url,
                aas_id,
            )
        else:
            register_one(
                my_registry_url, my_token,
                my_sm_registry_url, my_aas_env_url,
                partner_registry_url, partner_token,
                partner_sm_registry_url,
                aas_id,
            )

    print("\nDone.")


if __name__ == "__main__":
    main()
