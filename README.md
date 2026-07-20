# USAGE

This is a simple example of how to run the server and client in a docker container.

## First-time setup (once per machine, and again whenever your IP changes)

Everyone on the team runs their own copy of the stack under their own LAN IP.
Run this once to detect your IP, write it to `.env`, generate the config files
(nginx, Keycloak realm, aas-env, aas-web-ui) from their `*.template` sources,
and generate a matching TLS cert:

```bash
python3 setup_local_ip.py
```

Only edit the `*.template` files if you need to change the actual config -
the plain (non-`.template`) versions are generated and gitignored.

If `openssl` isn't on your PATH, the script will skip cert generation and you
can create `certs/server.crt` + `certs/server.key` yourself:

```bash
mkdir -p ./certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -keyout ./certs/server.key \
  -out ./certs/server.crt \
  -subj "/CN=<your-ip>" \
  -addext "subjectAltName=IP:<your-ip>"
```

## Run

```bash
docker compose up -d
```

## Open the UI: https://\<your-ip\>/

## Open the Keycloak admin dashboard: https://\<your-ip\>/auth

To stop and remove the container run:

```bash
docker compose down
```
