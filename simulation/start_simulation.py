#!/usr/bin/env python3
"""Start the MQTT gripper simulation from the host machine."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Publish simulated gripper telemetry over MQTT")
    parser.add_argument("--broker", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--topic", default="factory/pgn-plus-p-64-1/telemetry")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()

    simulator = Path(__file__).with_name("mqtt-publisher") / "simulator.py"
    environment = os.environ.copy()
    environment.update({
        "MQTT_BROKER_HOST": args.broker,
        "MQTT_BROKER_PORT": str(args.port),
        "MQTT_TOPIC": args.topic,
        "SIMULATION_INTERVAL": str(args.interval),
    })
    print(f"Starting MQTT simulation: {args.broker}:{args.port}/{args.topic}", flush=True)
    try:
        subprocess.run([sys.executable, str(simulator)], env=environment, check=True)
    except KeyboardInterrupt:
        print("Simulation stopped", flush=True)


if __name__ == "__main__":
    main()
