#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import sys
import time
import jwt as pyjwt  # pip install pyjwt

DID_WEB = os.getenv("DID_WEB", "did:web:172.17.255.170")
MOCK_SIGNING_KEY = os.getenv("MOCK_SIGNING_KEY", "dev-only-shared-secret")


class Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")

        print(f"{self.command} {self.path} body={body}", file=sys.stderr, flush=True)

        if self.path == "/presentations/query":
            self.handle_presentation_query()
            return

        self.send_json(404, {"error": "not_found"})

    def handle_presentation_query(self):
        now = int(time.time())

        vc_payload = {
            "iss": DID_WEB,
            "sub": DID_WEB,
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
            "vc": {
                "@context": [
                    "https://www.w3.org/2018/credentials/v1",
                    "https://w3id.org/tractusx-trust/v0.8",
                ],
                "type": ["VerifiableCredential", "MembershipCredential"],
                "issuer": DID_WEB,
                "credentialSubject": {
                    "id": DID_WEB,
                    "holderIdentifier": DID_WEB,
                },
            },
        }
        vc_jwt = pyjwt.encode(vc_payload, MOCK_SIGNING_KEY, algorithm="HS256")

        vp_payload = {
            "iss": DID_WEB,
            "aud": DID_WEB,
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
            "jti": f"urn:uuid:mock-{now}",
            "vp": {
                "@context": ["https://www.w3.org/2018/credentials/v1"],
                "type": ["VerifiablePresentation"],
                "verifiableCredential": [vc_jwt],
            },
        }
        vp_jwt = pyjwt.encode(vp_payload, MOCK_SIGNING_KEY, algorithm="HS256")

        response = {
            "@context": [
                "https://identity.foundation/presentation-exchange/submission/v1",
                "https://w3id.org/tractusx-trust/v0.8",
            ],
            "type": "PresentationResponseMessage",
            "presentation": [vp_jwt],
        }

        self.send_json(200, response)

    def send_json(self, status, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"BDRS mock listening on 0.0.0.0:{port}", file=sys.stderr, flush=True)
    server.serve_forever()