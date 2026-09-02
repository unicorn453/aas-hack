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
can create `config/certs/server.crt` + `config/certs/server.key` yourself:

```bash
mkdir -p ./config/certs
openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -keyout ./config/certs/server.key \
  -out ./config/certs/server.crt \
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

## EDC + Cross-server discoverability

This repository includes Tractus-X EDC services so other servers can discover and
connect to your data endpoints over the network.

1. Ensure your IP is current in `.env`:

```bash
python3 setup_local_ip.py
```

2. Start the stack:

```bash
docker compose up -d
```

3. Verify EDC endpoints are reachable from your host:

```bash
curl -k https://$HOST_ADDRESS:19191/api/dsp
curl -k https://$HOST_ADDRESS:19291/api/public
```

4. Discover shell offers from a partner server through EDC catalog only
   (no direct shell-descriptor push):

```bash
python3 tools/search_shells_via_edc.py --provider-url https://<partner-ip>
```

5. Optional: inspect the full catalog payload when debugging:

```bash
python3 tools/search_shells_via_edc.py --provider-url https://<partner-ip> --raw
```

Notes:
- This flow queries the partner through DSP via your local control plane
  management API (`/api/management/v3/catalog/request`).
- The default local management endpoint is `http://localhost:19193/api/management`
  with API key `password` (override via `--management-url` and `--api-key`).
- The provider DSP endpoint is expected to be HTTPS on port 19191:
  `https://<partner-ip>:19191/api/dsp`.
- If provider values differ, override with `--provider-dsp-url` and
  `--provider-participant-id`.

Troubleshooting:
- If EDC logs `Invalid URL host: ""` during catalog requests, one of the DSP URLs is empty or malformed.
  Check your CLI values and ensure `HOST_ADDRESS` is set by running `python3 setup_local_ip.py` before
  `docker compose up -d`.
- If you see `TLS connect error: wrong version number` or `HTTP 404 Not Found` on `/api/dsp`, the provider is
  probably not serving the DSP endpoint with the expected TLS certificate and path. Ensure the EDC containers were
  recreated after generating the certs, and then use `https://<partner-ip>:19191/api/dsp` or override
  `--provider-dsp-url` explicitly.
- If EDC logs DIM/BDRS token refresh errors or `No setting found for key edc.iam.sts.dim.url`, recreate the EDC
  containers after changing the mounted properties.
- For local testing, this repository starts small `dim-mock` and `bdrs-mock` services that answer the DIM/BDRS
  requests the EDC extensions expect, while Keycloak still serves the OAuth token endpoint used by the rest of the stack.
- The local DID document is served by nginx at `/.well-known/did.json`; rerun `python3 setup_local_ip.py` after your
  IP changes so the generated nginx config keeps the DID host in sync.
- The EDC containers now trust `config/certs/server.crt` directly through `JAVA_TOOL_OPTIONS`, so recreate the control
  plane and data plane after cert or IP changes.
