"""Subscribe to MQTT telemetry and update the local AAS TimeSeries record."""

import base64
import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import requests


def make_client():
    # Support Paho MQTT 1.x on the host and 2.x in the container image.
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    return mqtt.Client()


def encode_id(value):
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "factory/egp-40-n-n-b/telemetry")
AAS_BASE = os.getenv("AAS_BASE_URL", "http://aas-env:8081").rstrip("/")
KEYCLOAK = os.getenv("KEYCLOAK_URL", "http://keycloak:8080/auth").rstrip("/")
USERNAME = os.environ["KEYCLOAK_USERNAME"]
PASSWORD = os.environ["KEYCLOAK_PASSWORD"]
TIMESERIES_ID = os.environ["TIMESERIES_ID"]
VERIFY_TLS = os.getenv("AAS_VERIFY_TLS", "true").lower() not in {"0", "false", "no"}


class AasWriter:
    def __init__(self):
        self.token = None
        self.token_expiry = 0
        self.url = f"{AAS_BASE}/submodels/{encode_id(TIMESERIES_ID)}"

    def get_token(self):
        if self.token and time.time() < self.token_expiry - 30:
            return self.token
        response = requests.post(
            f"{KEYCLOAK}/realms/basyx/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "basyx-api",
                "client_secret": "basyx-api-secret",
                "username": USERNAME,
                "password": PASSWORD,
            },
            timeout=15,
            verify=VERIFY_TLS,
        )
        response.raise_for_status()
        payload = response.json()
        self.token = payload["access_token"]
        self.token_expiry = time.time() + int(payload.get("expires_in", 300))
        return self.token

    def write(self, telemetry):
        response = requests.get(self.url, headers={"Authorization": f"Bearer {self.get_token()}"}, timeout=15, verify=VERIFY_TLS)
        if response.status_code == 401:
            self.token = None
            response = requests.get(self.url, headers={"Authorization": f"Bearer {self.get_token()}"}, timeout=15, verify=VERIFY_TLS)
        response.raise_for_status()
        model = response.json()
        segments = next(x for x in model["submodelElements"] if x["idShort"] == "Segments")["value"]
        internal = next(x for x in segments if x["idShort"] == "InternalSegment")
        records = next(x for x in internal["value"] if x["idShort"] == "Records")["value"]
        record = next(x for x in records if x["idShort"] == "Record")
        values = {
            "Time": int(telemetry.get("time", time.time())),
            "JawPosition": float(telemetry["jawPosition"]),
            "GripForce": float(telemetry["gripForce"]),
            "Temperature": float(telemetry["temperature"]),
            "MotorCurrent": float(telemetry["motorCurrent"]),
            "CycleCount": int(telemetry["cycleCount"]),
            "CurrentState": str(telemetry["state"]),
        }
        for element in record["value"]:
            if element["idShort"] in values:
                element["value"] = str(values[element["idShort"]])
        now = datetime.now(timezone.utc).isoformat()
        for element in internal["value"]:
            if element["idShort"] == "LastUpdate":
                element["value"] = now
            elif element["idShort"] == "RecordCount":
                element["value"] = "1"
        put = requests.put(self.url, json=model, headers={"Authorization": f"Bearer {self.get_token()}"}, timeout=15, verify=VERIFY_TLS)
        if put.status_code == 401:
            self.token = None
            put = requests.put(self.url, json=model, headers={"Authorization": f"Bearer {self.get_token()}"}, timeout=15, verify=VERIFY_TLS)
        put.raise_for_status()


writer = AasWriter()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        raise RuntimeError(f"MQTT connection failed: {reason_code}")
    client.subscribe(MQTT_TOPIC, qos=1)
    print(f"Subscribed to {MQTT_TOPIC}", flush=True)


def on_message(client, userdata, message):
    try:
        writer.write(json.loads(message.payload))
        print(f"Updated AAS from {message.topic}", flush=True)
    except Exception as exc:
        print(f"Telemetry update failed: {exc}", flush=True)


client = make_client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_forever()
