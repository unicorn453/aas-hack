# MQTT live telemetry

This branch uses one direct two-site live-data path:

`your server: mqtt-publisher -> mqtt-broker -> remote server: mqtt-aas-subscriber -> remote AAS`

The bridge expects the existing remote AAS and its existing `TimeSeries`
submodel. It updates the single current `Record` in that submodel; it does not
create or attach an AAS/submodel.

## Remote server

On the computer that hosts the AAS Docker Compose stack, check out this branch
and start the two required services:

```bash
git checkout mqtt-live-simulation
MQTT_BROKER_HOST=<YOUR_SERVER_IP> \
docker compose up -d mqtt-aas-subscriber
docker compose logs -f mqtt-aas-subscriber
```

The subscriber uses the internal Compose name `keycloak` for authentication,
but connects to your server's MQTT broker using `MQTT_BROKER_HOST`.

Your server's port `1883` must be reachable from the remote server.

## Your server

On the local machine-side server, start its broker and the optional simulator:

```bash
docker compose --profile simulation up -d mqtt-broker mqtt-publisher
```

The publisher sends to the broker on your server. The remote subscriber reads
that broker directly; there is no separate forwarder service.

## Send telemetry

Publish JSON to:

```text
factory/egp-40-n-n-b/telemetry
```

Required fields are `jawPosition`, `gripForce`, `temperature`,
`motorCurrent`, `cycleCount`, and `state`. Optional `time` is an integer.

## Start simulation from the host

With the MQTT broker running, start simulated data without starting another
Docker service:

```bash
python3 simulation/start_simulation.py
```

The script publishes to `127.0.0.1:1883` by default. Use `--broker` and
`--port` when the broker is on another machine.

For a quick test from a machine that can reach the broker:

```bash
mosquitto_pub -h <AAS_SERVER_IP> -t factory/egp-40-n-n-b/telemetry \
  -m '{"jawPosition":20,"gripForce":35,"temperature":25,"motorCurrent":1.2,"cycleCount":4,"state":"GRIPPING"}'
```

Then inspect the subscriber log. The updated values are in the remote
`TimeSeries` submodel and can be read by the AAS web UI/API.

## Optional simulator

The simulator is deliberately separate and is not started by normal
`docker compose up -d`:

```bash
docker compose --profile simulation up -d mqtt-publisher
```

This MQTT listener currently allows anonymous connections for a trusted-LAN
demo. Add a Mosquitto password file and TLS before exposing port 1883 outside
that network.

## Same-machine temporary test

The file `docker-compose.test-remote.yml` starts a second backend stack with
separate volumes and host ports. Start the first stack with the broker and
publisher, then start the temporary second stack:

```bash
docker compose --profile simulation up -d mqtt-broker mqtt-publisher
MQTT_BROKER_HOST=host.docker.internal \
docker compose -p aas-remote-test -f docker-compose.test-remote.yml up -d
```

The second AAS API is available on `http://localhost:18081`. Its subscriber
reads the first stack's MQTT broker on port `1883` and updates the second AAS.
Stop and remove only the temporary stack with:

```bash
docker compose -p aas-remote-test -f docker-compose.test-remote.yml down
```
