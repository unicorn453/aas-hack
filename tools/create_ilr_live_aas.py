#!/usr/bin/env python3
"""Create a live-data copy of the ILR performance-plus AAS.

The copy references the original submodels and adds an IDTA 02008-1-1
TimeSeries submodel that the MQTT bridge keeps up to date. Both are also
registered in the AAS and submodel registries.
"""

import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "simulation"))

import simulate_timeseries as ts  # noqa: E402
from simulate_gripper import encode_id, request, token  # noqa: E402

SOURCE_AAS_ID = "https://example.org/ilr/ilr-performance-plus"
LIVE_AAS_ID = "https://example.org/ilr/ilr-performance-plus-live"
LIVE_TS_ID = f"{LIVE_AAS_ID}/sm/TimeSeries"


def put_or_post(server, bearer, collection, item_id, body):
    url = f"{server}/{collection}"
    try:
        request("POST", url, bearer, body)
        return "created"
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise
        request("PUT", f"{url}/{encode_id(item_id)}", bearer, body)
        return "updated"


def register(url, bearer, descriptor):
    try:
        request("POST", url, bearer, descriptor)
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="https://localhost")
    parser.add_argument("--public-url", default=None, help="Base URL written into registry endpoints")
    parser.add_argument("--registry-url", help="AAS registry, e.g. http://aas-registry:8080 (internal network only)")
    parser.add_argument("--submodel-registry-url", help="Submodel registry, e.g. http://submodel-registry:8080")
    parser.add_argument("--username", default="basyx-admin")
    parser.add_argument("--password", default="basyx-admin")
    args = parser.parse_args()
    server = args.server.rstrip("/")
    public = (args.public_url or server).rstrip("/")
    bearer = token(server, args.username, args.password)

    _, source = request("GET", f"{server}/shells/{encode_id(SOURCE_AAS_ID)}", bearer)

    ts.SUBMODEL_ID = LIVE_TS_ID
    submodel = ts.make_official_submodel()
    print("TimeSeries submodel", put_or_post(server, bearer, "submodels", LIVE_TS_ID, submodel))

    shell = copy.deepcopy(source)
    shell["id"] = LIVE_AAS_ID
    shell["idShort"] = f"{source.get('idShort', 'ILR')}Live"
    shell.setdefault("submodels", []).append({
        "type": "ModelReference",
        "keys": [{"type": "Submodel", "value": LIVE_TS_ID}],
    })
    print("Live shell", put_or_post(server, bearer, "shells", LIVE_AAS_ID, shell))

    asset = shell["assetInformation"]
    if not (args.registry_url and args.submodel_registry_url):
        print("Registry URLs not given; skipping registration (registries are not exposed by nginx)")
        return
    register(f"{args.registry_url.rstrip('/')}/shell-descriptors", bearer, {
        "id": LIVE_AAS_ID,
        "idShort": shell["idShort"],
        "assetKind": asset.get("assetKind", "Instance"),
        "globalAssetId": asset.get("globalAssetId"),
        "endpoints": [{
            "interface": "AAS-3.0",
            "protocolInformation": {
                "href": f"{public}/shells/{encode_id(LIVE_AAS_ID)}",
                "endpointProtocol": "https",
            },
        }],
    })
    register(f"{args.submodel_registry_url.rstrip('/')}/submodel-descriptors", bearer, {
        "id": LIVE_TS_ID,
        "idShort": "TimeSeries",
        "endpoints": [{
            "interface": "SUBMODEL-3.0",
            "protocolInformation": {
                "href": f"{public}/submodels/{encode_id(LIVE_TS_ID)}",
                "endpointProtocol": "https",
            },
        }],
    })
    print("Registered descriptors")


if __name__ == "__main__":
    main()
