"""Authenticated AASX upload facade.

The browser user must present a valid Keycloak user token. The facade then
uses the internal BaSyx admin service credential for the importer, preventing
the importer rollback path from requiring broad DELETE permissions from users.
"""

import cgi
import base64
import hashlib
import hmac
import json
import os
import ssl
import time
import tempfile
import zipfile
from io import BytesIO
from xml.etree import ElementTree
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AAS_BASE = os.getenv("AAS_BASE_URL", "http://aas-env:8081").rstrip("/")
KEYCLOAK = os.getenv("KEYCLOAK_URL", "http://keycloak:8080/auth").rstrip("/")
REGISTRY_BASE = os.getenv("AAS_REGISTRY_URL", "http://aas-registry:8080").rstrip("/")
SUBMODEL_REGISTRY_BASE = os.getenv("SUBMODEL_REGISTRY_URL", "http://submodel-registry:8080").rstrip("/")
EXTERNAL_URL = os.getenv("EXTERNAL_URL", "https://172.17.251.203").rstrip("/")
ADMIN_USERNAME = os.environ["KEYCLOAK_USERNAME"]
ADMIN_PASSWORD = os.environ["KEYCLOAK_PASSWORD"]
MAX_UPLOAD = 100 * 1024 * 1024
TLS_CONTEXT = ssl._create_unverified_context()


def json_request(url, data, headers):
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=30, context=TLS_CONTEXT) as response:
        return json.loads(response.read())


def b64decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_token(token):
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(b64decode(encoded_header))
        payload = json.loads(b64decode(encoded_payload))
        if header.get("alg") != "RS256":
            return False
        if not str(payload.get("iss", "")).endswith("/auth/realms/basyx"):
            return False
        if float(payload.get("exp", 0)) <= time.time():
            return False
        if float(payload.get("nbf", 0)) > time.time() + 30:
            return False
        roles = payload.get("realm_access", {}).get("roles", [])
        if "user" not in roles and "admin" not in roles:
            return False
        jwks = json_request(
            f"{KEYCLOAK}/realms/basyx/protocol/openid-connect/certs",
            None,
            {"Accept": "application/json"},
        )
        key = next(item for item in jwks["keys"] if item.get("kid") == header.get("kid"))
        modulus = int.from_bytes(b64decode(key["n"]), "big")
        exponent = int.from_bytes(b64decode(key["e"]), "big")
        signature = b64decode(encoded_signature)
        decoded = pow(int.from_bytes(signature, "big"), exponent, modulus).to_bytes(len(signature), "big")
        digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(
            f"{encoded_header}.{encoded_payload}".encode()
        ).digest()
        expected = b"\x00\x01" + b"\xff" * (len(signature) - len(digest_info) - 3) + b"\x00" + digest_info
        return hmac.compare_digest(decoded, expected)
    except Exception as exc:
        print(f"Token verification failed: {exc}", flush=True)
        return False


def admin_token():
    payload = urlencode({
        "grant_type": "password",
        "client_id": "basyx-api",
        "client_secret": "basyx-api-secret",
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
    }).encode()
    result = json_request(
        f"{KEYCLOAK}/realms/basyx/protocol/openid-connect/token",
        payload,
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    return result["access_token"]


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def first_value(element, wanted):
    for child in element.iter():
        if local_name(child.tag) == wanted and (child.text or "").strip():
            return (child.text or "").strip()
    return ""


def aasx_descriptors(content):
    """Extract registry descriptors from the XML administration shells in an AASX."""
    descriptors = {"aas": [], "submodels": []}
    with zipfile.ZipFile(BytesIO(content)) as package:
        for name in package.namelist():
            if not name.lower().endswith((".xml", ".aas.xml")):
                continue
            try:
                root = ElementTree.fromstring(package.read(name))
            except ElementTree.ParseError:
                continue
            for element in root.iter():
                kind = local_name(element.tag)
                if kind not in ("assetAdministrationShell", "submodel"):
                    continue
                identifier = first_value(element, "id")
                if not identifier:
                    continue
                encoded = base64.urlsafe_b64encode(identifier.encode()).decode().rstrip("=")
                if kind == "assetAdministrationShell":
                    descriptor = {
                        "id": identifier,
                        "idShort": first_value(element, "idShort") or identifier.rsplit("/", 1)[-1],
                        "assetKind": first_value(element, "assetKind") or "Instance",
                        "globalAssetId": first_value(element, "globalAssetId") or None,
                        "endpoints": [{
                            "interface": "AAS-3.0",
                            "protocolInformation": {
                                "href": f"{EXTERNAL_URL}/shells/{encoded}",
                                "endpointProtocol": "https",
                            },
                        }],
                    }
                    descriptors["aas"].append(descriptor)
                else:
                    descriptors["submodels"].append({
                        "id": identifier,
                        "idShort": first_value(element, "idShort") or identifier.rsplit("/", 1)[-1],
                        "endpoints": [{
                            "interface": "SUBMODEL-3.0",
                            "protocolInformation": {
                                "href": f"{EXTERNAL_URL}/submodels/{encoded}",
                                "endpointProtocol": "https",
                            },
                        }],
                    })
    return descriptors


def register_descriptors(content, token):
    descriptors = aasx_descriptors(content)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for descriptor in descriptors["aas"]:
        json_request(f"{REGISTRY_BASE}/shell-descriptors", json.dumps(descriptor).encode(), headers)
    for descriptor in descriptors["submodels"]:
        json_request(f"{SUBMODEL_REGISTRY_BASE}/submodel-descriptors", json.dumps(descriptor).encode(), headers)
    return {"aas": len(descriptors["aas"]), "submodels": len(descriptors["submodels"])}


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

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/upload":
            self.send_json(404, {"error": "not found"})
            return
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer ") or not verify_token(authorization[7:]):
            self.send_json(401, {"error": "authentication required"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_UPLOAD + 1024 * 1024:
                self.send_json(413, {"error": "AASX file is empty or exceeds the 100 MB limit"})
                return
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
            )
            uploaded = form["file"] if "file" in form else None
            if uploaded is None or not getattr(uploaded, "filename", None):
                self.send_json(400, {"error": "multipart field 'file' is required"})
                return
            filename = os.path.basename(uploaded.filename)
            content = uploaded.file.read(MAX_UPLOAD + 1)
            if len(content) > MAX_UPLOAD:
                self.send_json(413, {"error": "AASX file exceeds the 100 MB limit"})
                return
            boundary = "----BaSyxUploadFacadeBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
            importer_token = admin_token()
            request = Request(
                f"{AAS_BASE}/upload",
                data=body,
                headers={
                    "Authorization": f"Bearer {importer_token}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Content-Length": str(len(body)),
                },
                method="POST",
            )
            with urlopen(request, timeout=300, context=TLS_CONTEXT) as response:
                result = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(result)))
                self.end_headers()
                self.wfile.write(result)
        except HTTPError as exc:
            details = exc.read().decode(errors="replace")
            self.send_json(exc.code, {"error": "AASX importer rejected the file", "details": details[:2000]})
        except Exception as exc:
            print(f"AASX upload failed: {exc}", flush=True)
            self.send_json(502, {"error": "AASX upload service failed"})

    def log_message(self, *_):
        pass


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
