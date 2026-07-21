"""
Shared HTTP client for our BaSyx scripts (copy_shell.py, register_remote.py).

Core idea — the "clean rule":
    The token must always match the HOST of the URL being requested.

Background: every BaSyx stack only accepts tokens issued by its OWN
Keycloak. With cross-registration a descriptor comes from registry A, but
the endpoint href inside it points at server B — fetching it needs a token
from Keycloak B, not A. See SCRIPTS.md for details.

The TokenPool therefore keeps credentials per host, picks the matching
token for each request based on the URL host, caches tokens until shortly
before expiry, and fetches a fresh one once after a 401.
"""

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
import urllib3

from aas_python_http_client.util import string_to_base64url

# Self-signed certificates -> suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 10


@dataclass
class Credentials:
    """Keycloak credentials for ONE stack (hackathon defaults)."""
    realm: str = "basyx"
    client_id: str = "basyx-api"
    client_secret: str = "basyx-api-secret"
    username: str = "basyx-admin"
    password: str = "basyx-admin"


class TokenPool:
    """
    Manages credentials and tokens for multiple hosts.

    For every request the URL host decides which token is attached. URLs
    to hosts without registered credentials produce a clear error instead
    of a 401 from the server.
    """

    def __init__(self):
        self._creds: dict[str, tuple[str, Credentials]] = {}   # host -> (base_url, creds)
        self._tokens: dict[str, tuple[str, float]] = {}        # host -> (token, valid_until)
        self.session = requests.Session()
        self.session.verify = False  # self-signed certificates in the hackathon setup

    def add_host(self, base_url: str, creds: Credentials) -> None:
        """Register credentials for one stack."""
        host = urlparse(base_url).netloc
        self._creds[host] = (base_url.rstrip("/"), creds)

    def token_for(self, url: str, force_refresh: bool = False) -> str:
        """Return a valid token for the host of the given URL."""
        host = urlparse(url).netloc
        if host not in self._creds:
            known = ", ".join(sorted(self._creds)) or "(none)"
            raise KeyError(
                f"No credentials registered for host {host!r} "
                f"(known: {known}). The URL probably comes from a "
                f"cross-registered descriptor — add credentials for this "
                f"host via add_host() or --extra-host.")

        cached = self._tokens.get(host)
        if not force_refresh and cached and cached[1] > time.monotonic():
            return cached[0]

        base_url, creds = self._creds[host]
        response = self.session.post(
            f"{base_url}/auth/realms/{creds.realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "username": creds.username,
                "password": creds.password,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        # 30 s slack so the token does not expire mid-request
        valid_until = time.monotonic() + data.get("expires_in", 60) - 30
        self._tokens[host] = (data["access_token"], valid_until)
        return data["access_token"]

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute a request with the token matching the URL host."""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token_for(url)}"
        response = self.session.request(method, url, headers=headers,
                                        timeout=TIMEOUT, **kwargs)
        if response.status_code == 401:
            # Token may have been invalidated server-side -> fetch a fresh one once
            headers["Authorization"] = f"Bearer {self.token_for(url, force_refresh=True)}"
            response = self.session.request(method, url, headers=headers,
                                            timeout=TIMEOUT, **kwargs)
        return response


class Server:
    """
    One BaSyx stack (registry + repository behind nginx).

    All requests go through the shared TokenPool — including endpoint
    hrefs that point at OTHER hosts, which automatically get the right
    token.
    """

    def __init__(self, base_url: str, pool: TokenPool):
        self.base_url = base_url.rstrip("/")
        self.pool = pool

    def _get(self, url: str) -> dict:
        response = self.pool.request("GET", url)
        response.raise_for_status()
        return response.json()

    # --- Reading --------------------------------------------------------
    def list_shell_descriptors(self) -> list[dict]:
        """All shell descriptors (paginated response, field 'result')."""
        return self._get(f"{self.base_url}/shell-descriptors").get("result", [])

    def get_shell_descriptor(self, aas_id: str) -> dict:
        return self._get(
            f"{self.base_url}/shell-descriptors/{string_to_base64url(aas_id)}")

    def get_submodel_descriptor(self, sm_id: str) -> dict:
        return self._get(
            f"{self.base_url}/submodel-descriptors/{string_to_base64url(sm_id)}")

    def download_shell(self, aas_id: str) -> dict:
        """Load a shell via the endpoint URL stored in its descriptor."""
        descriptor = self.get_shell_descriptor(aas_id)
        href = descriptor["endpoints"][0]["protocolInformation"]["href"]
        return self._get(href)

    def download_submodel(self, sm_id: str) -> dict:
        """
        Load a submodel — resolve the endpoint via the submodel registry
        if possible, otherwise try {base_url}/submodels/{id} directly.
        """
        try:
            descriptor = self.get_submodel_descriptor(sm_id)
            href = descriptor["endpoints"][0]["protocolInformation"]["href"]
        except (requests.HTTPError, KeyError, IndexError):
            href = f"{self.base_url}/submodels/{string_to_base64url(sm_id)}"
        return self._get(href)

    # --- Writing --------------------------------------------------------
    def _upsert(self, collection: str, identifier: str, data: dict) -> str:
        """POST to /{collection}; on 409 PUT to the id instead."""
        response = self.pool.request(
            "POST", f"{self.base_url}/{collection}", json=data)
        if response.status_code == 409:
            response = self.pool.request(
                "PUT",
                f"{self.base_url}/{collection}/{string_to_base64url(identifier)}",
                json=data)
            response.raise_for_status()
            return "updated"
        response.raise_for_status()
        return "created"

    def upload_shell(self, shell: dict) -> str:
        return self._upsert("shells", shell["id"], shell)

    def upload_submodel(self, submodel: dict) -> str:
        return self._upsert("submodels", submodel["id"], submodel)

    # --- Writing/deleting descriptors (for cross-registration) -----------
    def upsert_shell_descriptor(self, descriptor: dict) -> str:
        return self._upsert("shell-descriptors", descriptor["id"], descriptor)

    def upsert_submodel_descriptor(self, descriptor: dict) -> str:
        return self._upsert("submodel-descriptors", descriptor["id"], descriptor)

    def _delete(self, url: str) -> None:
        response = self.pool.request("DELETE", url)
        response.raise_for_status()

    def delete_shell_descriptor(self, aas_id: str) -> None:
        self._delete(
            f"{self.base_url}/shell-descriptors/{string_to_base64url(aas_id)}")

    def delete_submodel_descriptor(self, sm_id: str) -> None:
        self._delete(
            f"{self.base_url}/submodel-descriptors/{string_to_base64url(sm_id)}")


def submodel_ids_of(shell: dict) -> list[str]:
    """Extract the ids of all submodels referenced in a shell JSON."""
    ids = []
    for reference in shell.get("submodels", []):
        for key in reference.get("keys", []):
            if key.get("type") == "Submodel":
                ids.append(key["value"])
    return ids


def add_credential_args(parser, prefixes: tuple[str, ...]) -> None:
    """Add the credential arguments for each prefix (e.g. 'source', 'target')."""
    for prefix in prefixes:
        parser.add_argument(f"--{prefix}-realm", default="basyx")
        parser.add_argument(f"--{prefix}-client-id", default="basyx-api")
        parser.add_argument(f"--{prefix}-client-secret", default="basyx-api-secret")
        parser.add_argument(f"--{prefix}-username", default="basyx-admin")
        parser.add_argument(f"--{prefix}-password", default="basyx-admin")
    parser.add_argument(
        "--extra-host", nargs=3, action="append", default=[],
        metavar=("URL", "USER", "PASS"),
        help="credentials for an additional host that endpoint hrefs may "
             "point at (repeatable)")


def credentials_from_args(args, prefix: str) -> Credentials:
    """Build a Credentials object from the argparse values of one prefix."""
    get = lambda name: getattr(args, f"{prefix}_{name}")
    return Credentials(realm=get("realm"), client_id=get("client_id"),
                       client_secret=get("client_secret"),
                       username=get("username"), password=get("password"))
