"""Keycloak token acquisition (OAuth2 Resource Owner Password Credentials grant).

Same grant type the aas-env registry integration already uses in
docker-compose.yml, so it works against this repo's own Keycloak realm
out of the box.
"""

from __future__ import annotations

import getpass
import time
from typing import Optional

import requests

from .config import ServerConfig

_token_cache: dict[str, tuple[str, float]] = {}


def get_token(server: ServerConfig) -> Optional[str]:
    if server.keycloak is None:
        return None

    grant_type = server.keycloak.grant_type
    cache_key = f"{server.keycloak.token_endpoint}:{grant_type}:{server.username}"
    cached = _token_cache.get(cache_key)
    if cached and cached[1] > time.time() + 5:
        return cached[0]

    data = {
        "grant_type": grant_type,
        "client_id": server.keycloak.client_id,
    }
    if server.keycloak.client_secret:
        data["client_secret"] = server.keycloak.client_secret

    if grant_type == "password":
        password = server.resolved_password()
        if password is None:
            password = getpass.getpass(f"Password for {server.username}@{server.name}: ")
        data["username"] = server.username
        data["password"] = password

    response = requests.post(
        server.keycloak.token_endpoint,
        data=data,
        verify=server.verify_tls,
        timeout=10,
    )
    if not response.ok:
        raise SystemExit(
            f"Login to '{server.name}' failed ({response.status_code}): {response.text}"
        )

    payload = response.json()
    token = payload["access_token"]
    _token_cache[cache_key] = (token, time.time() + payload.get("expires_in", 60))
    return token
