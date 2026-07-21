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

## Shared team Keycloak (single sign-on across stacks)

By default every stack runs its own Keycloak — tokens are then only valid
on the issuing stack, which is why cross-registered shells from a partner
cannot be opened in your own web UI (401: wrong token issuer).

To fix this, the whole team can share ONE Keycloak. One member hosts it,
everyone else points their stack at it:

```bash
# the hosting member (e.g. 192.168.56.76) — default, nothing changes:
python3 setup_local_ip.py

# every other member:
python3 setup_local_ip.py --keycloak-address 192.168.56.76
docker compose up -d
```

On non-hosting machines the local keycloak + keycloak-db containers stay
off (compose profile), and all token endpoints, JWT validation and the
web UI login go to the shared Keycloak (plain HTTP port 8084 for the
backend containers, proxied `/auth` for the browser). Tokens are then
valid on every stack: cross-registered shells open in any web UI, and
scripts need only one set of credentials.

Note for the hosting member: the realm is only imported into Keycloak on
first start. If your Keycloak volume predates this feature, allow all
redirect URIs once (Keycloak admin console → realm `basyx` → client
`basyx-web` → Valid redirect URIs `*`, Web origins `*`) or wipe the
volume (`docker compose down -v`) and start fresh.

## Python scripts (find / copy / cross-register shells)

See [SCRIPTS.md](SCRIPTS.md) for the client scripts, including how
cross-registry sharing works and why tokens must match the host being
queried.
