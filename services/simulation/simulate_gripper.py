#!/usr/bin/env python3
"""Create and continuously update simulated EGP gripper telemetry in BaSyx."""

import argparse
import base64
import json
import math
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def encode_id(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def request(method, url, token, body=None, content_type="application/json"):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=15, context=__import__("ssl")._create_unverified_context()) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {exc.code}: {detail}") from exc


def token(base, username, password):
    payload = urllib.parse.urlencode({
        "grant_type": "password",
        "client_id": "basyx-api",
        "client_secret": "basyx-api-secret",
        "username": username,
        "password": password,
    }).encode()
    req = urllib.request.Request(
        f"{base}/auth/realms/basyx/protocol/openid-connect/token",
        data=payload,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=15, context=__import__("ssl")._create_unverified_context()) as response:
        return json.loads(response.read())["access_token"]


def property_element(id_short, value_type, value):
    return {"modelType": "Property", "idShort": id_short, "valueType": value_type, "value": str(value)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="https://172.17.255.202")
    parser.add_argument("--username", default="basyx-admin")
    parser.add_argument("--password", default="basyx-admin")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    server = args.server.rstrip("/")
    aas_id = "https://example.org/aas/schunk/egp-40-n-n-b"
    submodel_id = "https://example.org/submodels/schunk/egp-40-n-n-b/gripperoperationaldata"
    token_value = token(server, args.username, args.password)
    submodels_url = f"{server}/submodels"
    submodel_url = f"{submodels_url}/{encode_id(submodel_id)}"

    telemetry = [
        property_element("CurrentState", "xs:string", "OPEN"),
        property_element("JawPosition", "xs:double", 0.0),
        property_element("GripForce", "xs:double", 0.0),
        property_element("Temperature", "xs:double", 24.0),
        property_element("MotorCurrent", "xs:double", 0.0),
        property_element("CycleCount", "xs:integer", 0),
        property_element("ErrorCode", "xs:string", "NONE"),
        property_element("LastUpdate", "xs:dateTime", datetime.now(timezone.utc).isoformat()),
    ]
    submodel = {
        "modelType": "Submodel",
        "id": submodel_id,
        "idShort": "GripperOperationalData",
        "semanticId": {"type": "ExternalReference", "keys": [{
            "type": "GlobalReference",
            "value": "https://example.org/semantics/gripper-operational-data/1/0",
        }]},
        "submodelElements": telemetry,
    }

    try:
        request("POST", submodels_url, token_value, submodel)
        print(f"Created submodel: {submodel_id}")
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise
        print("Submodel already exists; reusing it")

    ref = {"type": "ModelReference", "keys": [{"type": "Submodel", "value": submodel_id}]}
    try:
        request("POST", f"{server}/shells/{encode_id(aas_id)}/submodel-refs", token_value, ref)
        print("Attached submodel to the EGP AAS")
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise
        print("Submodel reference already exists; reusing it")

    cycle = 0
    while True:
        phase = time.monotonic() / 5.0
        opening = 32.0 + 28.0 * math.sin(phase)
        gripping = max(0.0, math.sin(phase))
        state = "GRIPPING" if gripping > 0.75 else ("CLOSED" if opening < 8 else "OPEN")
        if opening < 8 and state == "CLOSED":
            cycle += 1
        values = {
            "CurrentState": state,
            "JawPosition": round(opening, 2),
            "GripForce": round(80.0 * gripping + random.uniform(-1.0, 1.0), 2),
            "Temperature": round(24.0 + 2.5 * gripping + random.uniform(-0.2, 0.2), 2),
            "MotorCurrent": round(0.3 + 1.8 * gripping + random.uniform(-0.05, 0.05), 2),
            "CycleCount": cycle,
            "ErrorCode": "NONE",
            "LastUpdate": datetime.now(timezone.utc).isoformat(),
        }
        for id_short, value in values.items():
            element_url = f"{submodel_url}/submodel-elements/{id_short}"
            value_type = "xs:string" if isinstance(value, str) else ("xs:integer" if id_short == "CycleCount" else "xs:double")
            if id_short == "LastUpdate":
                value_type = "xs:dateTime"
            request("PUT", element_url, token_value, property_element(id_short, value_type, value))
        print(json.dumps(values), flush=True)
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
