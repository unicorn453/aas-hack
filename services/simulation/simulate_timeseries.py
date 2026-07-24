#!/usr/bin/env python3
"""Create and update PGN gripper telemetry using IDTA 02008-1-1 Time Series Data."""

import argparse
import copy
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from simulate_gripper import encode_id, property_element, request, token


SERVER = "https://172.17.255.202"
AAS_ID = "https://example.org/aas/schunk/pgn-plus-p-64-1"
SUBMODEL_ID = "https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries"
TS = "https://admin-shell.io/idta/TimeSeries"


def ref(value, key_type="GlobalReference"):
    return {"type": "ExternalReference", "keys": [{"type": key_type, "value": value}]}


def collection(id_short, semantic, values, cardinality=None):
    result = {"idShort": id_short, "semanticId": ref(semantic), "value": values, "modelType": "SubmodelElementCollection"}
    if cardinality:
        result["qualifiers"] = [{"type": "Cardinality", "valueType": "xs:string", "value": cardinality}]
    return result


def make_submodel():
    record_definition = collection("Record", f"{TS}/Record/1/1", [
        property_element("Time", "xs:long", 0),
        property_element("JawPosition", "xs:double", 0),
        property_element("GripForce", "xs:double", 0),
        property_element("Temperature", "xs:double", 0),
        property_element("MotorCurrent", "xs:double", 0),
        property_element("CycleCount", "xs:long", 0),
        property_element("CurrentState", "xs:string", "OPEN"),
    ])
    metadata = collection("Metadata", f"{TS}/Metadata/1/1", [
        property_element("Name", "xs:string", "EGP gripper operational telemetry"),
        property_element("Description", "xs:string", "Simulated live telemetry for the EGP gripper"),
        collection("Record", f"{TS}/Record/1/1", [
            property_element("Time", "xs:long", 0),
            property_element("JawPosition", "xs:double", 0),
            property_element("GripForce", "xs:double", 0),
            property_element("Temperature", "xs:double", 0),
            property_element("MotorCurrent", "xs:double", 0),
            property_element("CycleCount", "xs:long", 0),
            property_element("CurrentState", "xs:string", "OPEN"),
        ]),
    ])
    record = collection("Record", f"{TS}/Record/1/1", [
        property_element("Time", "xs:long", 0),
        property_element("JawPosition", "xs:double", 0),
        property_element("GripForce", "xs:double", 0),
        property_element("Temperature", "xs:double", 0),
        property_element("MotorCurrent", "xs:double", 0),
        property_element("CycleCount", "xs:long", 0),
        property_element("CurrentState", "xs:string", "OPEN"),
    ])
    internal = collection("InternalSegment", f"{TS}/Segments/InternalSegment/1/1", [
        property_element("RecordCount", "xs:long", 1),
        property_element("StartTime", "xs:string", datetime.now(timezone.utc).isoformat()),
        property_element("SamplingInterval", "xs:long", 2),
        property_element("SamplingRate", "xs:long", 1),
        property_element("State", "xs:string", "RUNNING"),
        property_element("LastUpdate", "xs:string", datetime.now(timezone.utc).isoformat()),
        collection("Records", f"{TS}/Records/1/1", [record], "One"),
    ], "ZeroToMany")
    segments = collection("Segments", f"{TS}/Segments/1/1", [internal], "One")
    return {
        "modelType": "Submodel",
        "kind": "Instance",
        "id": SUBMODEL_ID,
        "idShort": "TimeSeries",
        "semanticId": {"type": "ModelReference", "keys": [{"type": "Submodel", "value": f"{TS}/1/1"}]},
        "submodelElements": [metadata, segments],
    }


def make_official_submodel():
    """Instantiate the checked-in IDTA 02008-1-1 template exactly."""
    template_path = Path(__file__).resolve().parents[2] / "converters" / "excel-to-aasx" / "third_party" / "admin-shell-io" / "submodel-templates" / "published" / "Time Series Data" / "1" / "1" / "IDTA 02008-1-1_Template_TimeSeriesData.json"
    model = copy.deepcopy(json.loads(template_path.read_text())["submodels"][0])
    model["kind"] = "Instance"
    model["id"] = SUBMODEL_ID
    model["idShort"] = "TimeSeries"
    metadata = next(x for x in model["submodelElements"] if x["idShort"] == "Metadata")
    metadata_record = next(x for x in metadata["value"] if x["idShort"] == "Record")
    internal = next(x for x in next(x for x in model["submodelElements"] if x["idShort"] == "Segments")["value"] if x["idShort"] == "InternalSegment")
    record = next(x for x in next(x for x in internal["value"] if x["idShort"] == "Records")["value"] if x["idShort"] == "Record")
    sample = next(x for x in metadata_record["value"] if x["idShort"] != "Time")
    variables = []
    for name, value_type, semantic in [
        ("JawPosition", "xs:double", "https://example.org/semantics/gripper/JawPosition/1/0"),
        ("GripForce", "xs:double", "https://example.org/semantics/gripper/GripForce/1/0"),
        ("Temperature", "xs:double", "https://example.org/semantics/gripper/Temperature/1/0"),
        ("MotorCurrent", "xs:double", "https://example.org/semantics/gripper/MotorCurrent/1/0"),
        ("CycleCount", "xs:long", "https://example.org/semantics/gripper/CycleCount/1/0"),
        ("CurrentState", "xs:string", "https://example.org/semantics/gripper/CurrentState/1/0"),
    ]:
        element = copy.deepcopy(sample)
        element["idShort"] = name
        element["valueType"] = value_type
        element["semanticId"]["keys"][0]["value"] = semantic
        variables.append(element)
    time_element = next(x for x in metadata_record["value"] if x["idShort"] == "Time")
    metadata_record["value"] = [time_element] + variables
    record["value"] = [copy.deepcopy(x) for x in metadata_record["value"]]
    now = datetime.now(timezone.utc).isoformat()
    segment_values = {"RecordCount": "1", "StartTime": now, "SamplingInterval": "2", "SamplingRate": "1", "State": "RUNNING", "LastUpdate": now}
    for element in internal["value"]:
        if element["idShort"] in segment_values:
            element["value"] = segment_values[element["idShort"]]
    for element in metadata["value"]:
        if element["idShort"] == "Name": element["value"][0]["text"] = "EGP gripper live telemetry"
        if element["idShort"] == "Description": element["value"][0]["text"] = "Simulated operational data for the EGP gripper"
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default=SERVER)
    parser.add_argument("--username", default="basyx-admin")
    parser.add_argument("--password", default="basyx-admin")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    server = args.server.rstrip("/")
    bearer = token(server, args.username, args.password)
    submodels = f"{server}/submodels"
    submodel = f"{submodels}/{encode_id(SUBMODEL_ID)}"
    model = make_official_submodel()
    try:
        request("POST", submodels, bearer, model)
        print("Created IDTA 02008-1-1 TimeSeries submodel", flush=True)
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise
        print("TimeSeries submodel already exists", flush=True)
    try:
        request("POST", f"{server}/shells/{encode_id(AAS_ID)}/submodel-refs", bearer, {"type": "ModelReference", "keys": [{"type": "Submodel", "value": SUBMODEL_ID}]})
        print("Attached TimeSeries submodel to PGN AAS", flush=True)
    except RuntimeError as exc:
        if "HTTP 409" not in str(exc):
            raise
        print("TimeSeries reference already exists", flush=True)

    cycle = 0
    start_time = time.time()
    while True:
        phase = time.monotonic() / 5.0
        position = 32.0 + 28.0 * math.sin(phase)
        grip = max(0.0, math.sin(phase))
        state = "GRIPPING" if grip > 0.75 else ("CLOSED" if position < 8 else "OPEN")
        if state == "CLOSED":
            cycle += 1
        values = {
            "Time": int(time.time() - start_time),
            "JawPosition": round(position, 2),
            "GripForce": round(max(0.0, 80.0 * grip + random.uniform(-1, 1)), 2),
            "Temperature": round(24.0 + 2.5 * grip + random.uniform(-0.2, 0.2), 2),
            "MotorCurrent": round(0.3 + 1.8 * grip + random.uniform(-0.05, 0.05), 2),
            "CycleCount": cycle,
            "CurrentState": state,
        }
        segments = next(x for x in model["submodelElements"] if x["idShort"] == "Segments")
        internal = next(x for x in segments["value"] if x["idShort"] == "InternalSegment")
        records = next(x for x in internal["value"] if x["idShort"] == "Records")
        record = next(x for x in records["value"] if x["idShort"] == "Record")
        for element in record["value"]:
            if element["idShort"] in values:
                element["value"] = str(values[element["idShort"]])
        for element in internal["value"]:
            if element["idShort"] == "LastUpdate":
                element["value"] = datetime.now(timezone.utc).isoformat()
            if element["idShort"] == "RecordCount":
                element["value"] = str(len(records["value"]))
        request("PUT", submodel, bearer, model)
        print(values, flush=True)
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
