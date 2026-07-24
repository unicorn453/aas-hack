"""Publish simulated EGP gripper telemetry over MQTT."""

import json
import math
import os
import random
import time

import paho.mqtt.client as mqtt


def make_client():
    # Support both Paho MQTT 1.x on the host and 2.x in the container image.
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    return mqtt.Client()


host = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
topic = os.getenv("MQTT_TOPIC", "factory/pgn-plus-p-64-1/telemetry")
interval = float(os.getenv("SIMULATION_INTERVAL", "2"))
client = make_client()
client.connect(host, port, 60)
client.loop_start()
cycle = 0
start = time.time()

try:
    while True:
        phase = time.monotonic() / 5
        position = 32 + 28 * math.sin(phase)
        grip = max(0, math.sin(phase))
        state = "GRIPPING" if grip > 0.75 else ("CLOSED" if position < 8 else "OPEN")
        if state == "CLOSED":
            cycle += 1
        payload = {
            "time": int(time.time() - start),
            "jawPosition": round(position, 2),
            "gripForce": round(max(0, 80 * grip + random.uniform(-1, 1)), 2),
            "temperature": round(24 + 2.5 * grip + random.uniform(-0.2, 0.2), 2),
            "motorCurrent": round(0.3 + 1.8 * grip + random.uniform(-0.05, 0.05), 2),
            "cycleCount": cycle,
            "state": state,
        }
        client.publish(topic, json.dumps(payload), qos=1)
        print(json.dumps(payload), flush=True)
        time.sleep(interval)
finally:
    client.loop_stop()
    client.disconnect()
