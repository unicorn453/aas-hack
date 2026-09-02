#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import json
import os
import sys
import time


DID_WEB = os.getenv("DID_WEB", "did:web:172.17.255.170")


def base64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_jwt():
    now = int(time.time())

    header = {
        "alg": "none",
        "typ": "JWT",
    }

    payload = {
        "iss": "http://dim-mock:8080",
        "sub": DID_WEB,
        "scope": "read",
        "iat": now,
        "exp": now + 3600,
    }

    header_part = base64url(
        json.dumps(header, separators=(",", ":")).encode()
    )

    payload_part = base64url(
        json.dumps(payload, separators=(",", ":")).encode()
    )

    # alg=none JWT -> empty signature
    return f"{header_part}.{payload_part}."


class Handler(BaseHTTPRequestHandler):

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))

        if length:
            return self.rfile.read(length).decode(
                "utf-8",
                errors="replace"
            )

        return ""

    def _send_json(self, status, response):
        payload = json.dumps(response).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        body = self._read_body()

        print(
            f"{self.command} {self.path} body={body}",
            file=sys.stderr,
            flush=True,
        )

        if self.path.endswith(
            "/auth/realms/basyx/protocol/openid-connect/token"
        ):
            jwt = create_jwt()

            # IMPORTANT:
            # grantAccess MUST be a STRING for this EDC version.
            response = {
                "jwt": jwt
            }

            print(
                f"DIM response={json.dumps(response)}",
                file=sys.stderr,
                flush=True,
            )

            self._send_json(200, response)
            return

        self._send_json(
            200,
            {"result": "ok"}
        )

    def do_GET(self):
        self._send_json(200, {"result": "ok"})

    def do_PUT(self):
        self._send_json(200, {"result": "ok"})

    def do_DELETE(self):
        self._send_json(200, {"result": "ok"})

    def do_PATCH(self):
        self._send_json(200, {"result": "ok"})

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    name = os.getenv("MOCK_NAME", "DIM")

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        f"{name} mock listening on 0.0.0.0:{port}",
        file=sys.stderr,
        flush=True
    )

    server.serve_forever()