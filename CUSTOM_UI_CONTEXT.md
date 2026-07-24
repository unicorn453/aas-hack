# Custom UI Handoff Context

This repository contains a BaSyx AAS server for a Schunk PGN+ P 64-1 gripper, a public read-only DPP facade, Keycloak authentication, RBAC rules, MQTT live telemetry, and simulator scripts.

## Runtime services

```text
aas-env              Protected AAS and submodel repository
aas-registry         Protected AAS registry
submodel-registry    Protected submodel registry
keycloak             Authentication and token issuer
mongodb              AAS persistence
mqtt-broker          MQTT telemetry broker
mqtt-aas-subscriber  MQTT-to-TimeSeries updater
dpp-public-api       Anonymous read-only facade for static DPP data
aas-web-ui            Existing BaSyx Web UI; keep it unchanged
dpp-web-ui            Professional DPP website
```

## Authentication model

The backend remains protected. The public facade uses an internal service credential and exposes only allowlisted static DPP data. It does not forward caller credentials.

```text
Public static DPP → /public/... → anonymous read-only facade
Protected AAS     → /shells/... and /submodels/... → Keycloak bearer token
Live TimeSeries   → protected and admin-only
```

Keycloak demo users from the development realm:

```text
basyx-user / basyx-user
basyx-admin / basyx-admin
```

The frontend must not hard-code these credentials. They are only for manual development testing.

## MQTT and live data

The simulator publishes JSON telemetry to:

```text
factory/pgn-plus-p-64-1/telemetry
```

Required telemetry fields:

```json
{
  "jawPosition": 20,
  "gripForce": 35,
  "temperature": 25,
  "motorCurrent": 1.2,
  "cycleCount": 4,
  "state": "GRIPPING"
}
```

The MQTT subscriber writes these values into the protected IDTA TimeSeries submodel. The browser should read the resulting TimeSeries through the authenticated BaSyx REST API using polling.

## Setup for another workspace

From the repository root:

```bash
python3 setup_local_ip.py
docker compose up -d
```

Start the simulator when required:

```bash
python3 simulation/start_simulation.py
```

The custom UI should be started separately after implementation:

```bash
docker compose up -d --build dpp-web-ui
```

## Important implementation warning

The normal BaSyx Web UI applies authentication per configured infrastructure. The custom UI is being created specifically to provide a single page where public static DPP data and protected admin-only live data coexist.

Do not solve the problem by disabling backend authorization globally.
