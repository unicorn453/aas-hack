"""Expose only approved static DPP submodels without forwarding user auth."""

import base64
import json
import os
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen



def encode_id(value):
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_id(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()


PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def public_endpoint(endpoint, public_prefix):
    """Rewrite an upstream repository endpoint to this public facade."""
    if not isinstance(endpoint, dict):
        return endpoint
    rewritten = dict(endpoint)
    if isinstance(rewritten.get("protocolInformation"), dict):
        protocol = dict(rewritten["protocolInformation"])
        href = protocol.get("href")
        if isinstance(href, str):
            parsed = urlsplit(href)
            path = parsed.path
            if "/shells/" in path:
                path = path.replace("/shells/", "/public/shells/", 1)
            elif "/submodels/" in path:
                path = path.replace("/submodels/", "/public/submodels/", 1)
            if PUBLIC_BASE_URL:
                public_origin = urlsplit(PUBLIC_BASE_URL)
                protocol["href"] = urlunsplit(
                    (public_origin.scheme, public_origin.netloc, path, "", "")
                )
            else:
                protocol["href"] = urlunsplit(
                    (parsed.scheme, parsed.netloc, path, "", "")
                )
        rewritten["protocolInformation"] = protocol
    return rewritten


def rewrite_descriptors(body, public_prefix):
    if not isinstance(body, dict) or not isinstance(body.get("result"), list):
        return body
    rewritten = dict(body)
    result = []
    for descriptor in body["result"]:
        item = dict(descriptor)
        if isinstance(item.get("endpoints"), list):
            item["endpoints"] = [
                public_endpoint(endpoint, public_prefix)
                for endpoint in item["endpoints"]
            ]
        result.append(item)
    rewritten["result"] = result
    return rewritten


def allow_descriptors(body, allowed_ids):
    if isinstance(body, list):
        return [item for item in body if is_public_aas_id(item.get("id", ""))]
    if isinstance(body, dict) and isinstance(body.get("result"), list):
        filtered = dict(body)
        filtered["result"] = [
            item for item in body["result"] if is_public_aas_id(item.get("id", ""))
        ]
        return filtered
    return body


AAS_BASE = os.getenv("AAS_BASE_URL", "http://aas-env:8081").rstrip("/")
KEYCLOAK = os.getenv("KEYCLOAK_URL", "http://keycloak:8080/auth").rstrip("/")
USERNAME = os.environ["KEYCLOAK_USERNAME"]
PASSWORD = os.environ["KEYCLOAK_PASSWORD"]
PUBLIC_IDS = {
    value.strip()
    for value in os.getenv("PUBLIC_SUBMODEL_IDS", "").split(",")
    if value.strip()
}
PUBLIC_AAS_IDS = {
    value.strip()
    for value in os.getenv("PUBLIC_AAS_IDS", "").split(",")
    if value.strip()
}
PRIVATE_SUBMODEL_PATTERNS = tuple(
    value.strip().lower()
    for value in os.getenv(
        "PRIVATE_SUBMODEL_PATTERNS", "timeseries,telemetry,live"
    ).split(",")
    if value.strip()
)


def is_public_aas_id(value):
    return not PUBLIC_AAS_IDS or value in PUBLIC_AAS_IDS


def is_public_submodel_id(value):
    if PUBLIC_IDS:
        return value in PUBLIC_IDS
    lowered = value.lower()
    return not any(pattern in lowered for pattern in PRIVATE_SUBMODEL_PATTERNS)


class Client:
    def __init__(self):
        self.token = None
        self.expires_at = 0
        self.token_lock = threading.Lock()

    def token_value(self):
        with self.token_lock:
            if self.token and time.time() < self.expires_at - 30:
                return self.token
            request = Request(
                f"{KEYCLOAK}/realms/basyx/protocol/openid-connect/token",
                data=urlencode({
                    "grant_type": "password",
                    "client_id": "basyx-api",
                    "client_secret": "basyx-api-secret",
                    "username": USERNAME,
                    "password": PASSWORD,
                }).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urlopen(request, timeout=15, context=ssl._create_unverified_context()) as response:
                body = json.loads(response.read())
            self.token = body["access_token"]
            self.expires_at = time.time() + int(body.get("expires_in", 300))
            return self.token

    def get_json(self, url):
        for attempt in range(2):
            request = Request(url, headers={"Authorization": f"Bearer {self.token_value()}"})
            try:
                with urlopen(request, timeout=15, context=ssl._create_unverified_context()) as response:
                    return json.loads(response.read())
            except HTTPError as exc:
                if exc.code == 401 and attempt == 0:
                    self.token = None
                    continue
                raise

    def get_submodel(self, submodel_id):
        return self.get_json(f"{AAS_BASE}/submodels/{encode_id(submodel_id)}")

    def get_shell(self, shell_id):
        shell = self.get_json(f"{AAS_BASE}/shells/{encode_id(shell_id)}")
        refs = []
        for ref in shell.get("submodels", []):
            keys = ref.get("keys", [])
            if any(is_public_submodel_id(key.get("value", "")) for key in keys):
                refs.append(ref)
        shell["submodels"] = refs
        return shell

    def get_registry(self, base, path):
        return self.get_json(f"{base.rstrip('/')}/{path.lstrip('/')}")


client = Client()


def public_registry_ids(path, predicate):
    body = client.get_registry(
        "http://aas-registry:8080" if "shell" in path else "http://submodel-registry:8080",
        path,
    )
    items = body.get("result", []) if isinstance(body, dict) else body
    return [item.get("id") for item in items if predicate(item.get("id", ""))]


def public_submodel_ids_from_shells():
    ids = []
    seen = set()
    for shell_id in public_registry_ids("/shell-descriptors", is_public_aas_id):
        shell = client.get_shell(shell_id)
        for reference in shell.get("submodels", []):
            for key in reference.get("keys", []):
                submodel_id = key.get("value", "")
                if is_public_submodel_id(submodel_id) and submodel_id not in seen:
                    seen.add(submodel_id)
                    ids.append(submodel_id)
    return ids


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        clean_path = self.path.split("?", 1)[0]
        if clean_path == "/public/shell-descriptors":
            try:
                body = client.get_registry("http://aas-registry:8080", "/shell-descriptors")
                body = allow_descriptors(body, PUBLIC_AAS_IDS)
                body = rewrite_descriptors(body, "/public/shells/")
                self.send_json(200, body)
            except Exception as exc:
                print(f"Public shell descriptor read failed: {exc}", flush=True)
                self.send_json(502, {"error": "upstream read failed"})
            return
        if clean_path == "/public/submodel-descriptors":
            try:
                body = client.get_registry("http://submodel-registry:8080", "/submodel-descriptors")
                if isinstance(body, dict) and isinstance(body.get("result"), list):
                    filtered = dict(body)
                    filtered["result"] = [
                        item for item in body["result"]
                        if is_public_submodel_id(item.get("id", ""))
                    ]
                    body = filtered
                body = rewrite_descriptors(body, "/public/submodels/")
                self.send_json(200, body)
            except Exception as exc:
                print(f"Public submodel descriptor read failed: {exc}", flush=True)
                self.send_json(502, {"error": "upstream read failed"})
            return
        if clean_path == "/public/shells":
            try:
                self.send_json(200, {
                    "paging_metadata": {},
                    "result": [
                        client.get_shell(shell_id)
                        for shell_id in public_registry_ids("/shell-descriptors", is_public_aas_id)
                    ],
                })
            except Exception as exc:
                print(f"Public shell collection read failed: {exc}", flush=True)
                self.send_json(502, {"error": "upstream read failed"})
            return
        if clean_path == "/public/submodels":
            try:
                self.send_json(200, {
                    "paging_metadata": {},
                    "result": [
                        client.get_submodel(submodel_id)
                        for submodel_id in public_submodel_ids_from_shells()
                    ],
                })
            except Exception as exc:
                print(f"Public submodel collection read failed: {exc}", flush=True)
                self.send_json(502, {"error": "upstream read failed"})
            return
        shell_prefix = "/public/shells/"
        if clean_path.startswith(shell_prefix):
            try:
                shell_id = decode_id(clean_path[len(shell_prefix):])
                if not is_public_aas_id(shell_id):
                    self.send_json(404, {"error": "AAS is not public"})
                    return
                self.send_json(200, client.get_shell(shell_id))
            except Exception as exc:
                print(f"Public shell read failed: {exc}", flush=True)
                self.send_json(502, {"error": "upstream read failed"})
            return
        prefix = "/public/submodels/"
        if not clean_path.startswith(prefix):
            self.send_json(404, {"error": "not found"})
            return
        try:
            submodel_id = decode_id(clean_path[len(prefix):])
            if not is_public_submodel_id(submodel_id):
                self.send_json(404, {"error": "submodel is not public"})
                return
            self.send_json(200, client.get_submodel(submodel_id))
        except Exception as exc:
            print(f"Public DPP read failed: {exc}", flush=True)
            self.send_json(502, {"error": "upstream read failed"})

    def do_POST(self):
        self.send_json(405, {"error": "read-only endpoint"})

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def log_message(self, *_):
        pass


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
