"""Load and validate the aas-cli server configuration file (servers.yaml)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONFIG_NAMES = ("aas-cli.yaml", "servers.yaml")


@dataclass
class KeycloakConfig:
    url: str
    realm: str = "basyx"
    client_id: str = "basyx-api"
    client_secret: Optional[str] = None

    @property
    def token_endpoint(self) -> str:
        return f"{self.url.rstrip('/')}/realms/{self.realm}/protocol/openid-connect/token"


@dataclass
class ServerConfig:
    name: str
    url: str
    registry_url: Optional[str] = None
    verify_tls: bool = True
    keycloak: Optional[KeycloakConfig] = None
    username: Optional[str] = None
    password: Optional[str] = None
    password_env: Optional[str] = None

    def resolved_password(self) -> Optional[str]:
        if self.password_env:
            value = os.environ.get(self.password_env)
            if value:
                return value
        return self.password


def find_config(explicit: Optional[str] = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise SystemExit(f"Config file not found: {path}")
        return path

    env_path = os.environ.get("AAS_CLI_CONFIG")
    if env_path:
        return find_config(env_path)

    for name in DEFAULT_CONFIG_NAMES:
        candidate = Path.cwd() / name
        if candidate.exists():
            return candidate

    user_config = Path.home() / ".config" / "aas-cli" / "servers.yaml"
    if user_config.exists():
        return user_config

    raise SystemExit(
        "No config file found. Looked for ./aas-cli.yaml, ./servers.yaml, "
        f"$AAS_CLI_CONFIG and {user_config}.\n"
        "Run 'aas-cli init' to create one from this repo's join.py output, "
        "or copy servers.example.yaml."
    )


def load_servers(config_path: Optional[str] = None) -> dict[str, ServerConfig]:
    path = find_config(config_path)
    raw = yaml.safe_load(path.read_text()) or {}
    servers_raw = raw.get("servers", {})

    servers: dict[str, ServerConfig] = {}
    for name, entry in servers_raw.items():
        kc_raw = entry.get("keycloak")
        keycloak = None
        if kc_raw:
            keycloak = KeycloakConfig(
                url=kc_raw["url"],
                realm=kc_raw.get("realm", "basyx"),
                client_id=kc_raw.get("client_id", "basyx-api"),
                client_secret=kc_raw.get("client_secret"),
            )
        servers[name] = ServerConfig(
            name=name,
            url=entry["url"],
            registry_url=entry.get("registry_url"),
            verify_tls=entry.get("verify_tls", True),
            keycloak=keycloak,
            username=entry.get("username"),
            password=entry.get("password"),
            password_env=entry.get("password_env"),
        )
    return servers


def get_server(name: str, config_path: Optional[str] = None) -> ServerConfig:
    servers = load_servers(config_path)
    try:
        return servers[name]
    except KeyError:
        available = ", ".join(sorted(servers)) or "(none configured)"
        raise SystemExit(f"Unknown server '{name}'. Configured servers: {available}")
