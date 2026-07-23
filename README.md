# AAS Hack — Standalone Node

Every machine that clones this repo runs a **complete, independent**
BaSyx stack: its own Keycloak, its own AAS-/Submodel-Registry, its own
AAS-Environment + web UI, all behind HTTPS (nginx, self-signed
certificate). There is no shared host, no single point of failure, and
no assumption that any other machine is reachable.

```
        YOUR MACHINE                              PARTNER'S MACHINE
        ┌───────────────────────────┐             ┌───────────────────────────┐
        │ nginx :443 (HTTPS)        │             │ nginx :443 (HTTPS)        │
        │  Keycloak  Registry (AAS  │  aas-cli    │  Keycloak  Registry (AAS  │
        │  (login)   + Submodel)    │◄───────────►│  (login)   + Submodel)    │
        │  AAS-Env + Web UI         │  up/download │  AAS-Env + Web UI         │
        └───────────────────────────┘             └───────────────────────────┘
```

Exchanging shells with a teammate or an external partner is a deliberate
action via [`aas-cli`](aas-cli/README.md) (`upload`/`download` against
their server) — not something that happens automatically through a
shared registry.

## Setup (2 commands)

```bash
python3 join.py
docker compose up -d
```

Then open `https://<your-own-ip>/` (accept the certificate warning —
self-signed) and log in with `basyx-admin` / `basyx-admin`.

If your IP changes (new day, different network): run `join.py` again and
`docker compose up -d` (restarts the changed containers).

## How it works

- **Uploading your own shells:** Web UI → Upload (AASX/JSON/XML), or
  `aas-cli upload --server local --file ...`. Your server registers every
  shell **automatically** in your **own** registry (BaSyx registry
  integration) — this only makes it visible in your own web UI, nothing
  is sent anywhere else.
- **Sending a shell to a teammate or partner:** `aas-cli upload --server
  <their-name> --file ...` — see [aas-cli/README.md](aas-cli/README.md)
  for several worked examples (listing, uploading, downloading, backing
  up, connecting to a partner with `password` or `client_credentials`
  auth).
- **Everyone logs in against their own Keycloak.** Different servers can
  use entirely different realms/clients/credentials — `aas-cli`'s
  `servers.yaml` keeps each server's auth config independent (see
  `client_credentials` support for partners who use a service-account
  client instead of personal logins).
- **Product made of parts from others:** once you've pulled a partner's
  submodel via `aas-cli download`, a new shell can reference it by ID
  (ModelReference).

| Service | URL |
|---|---|
| Your own web UI + repo | `https://<your-own-ip>/` |
| Your own registries | `https://<your-own-ip>/shell-descriptors`, `/submodel-descriptors` |
| Your own Keycloak (Admin: admin/admin) | `https://<your-own-ip>/auth` |

## Security

- Browser traffic runs entirely over **HTTPS** (nginx, self-signed
  certificate per machine). Nothing needs to be exposed beyond 80/443 —
  Keycloak and the registries are only reachable through nginx, not on
  separate LAN ports.
- Every API requires a Keycloak token: `admin` may write, `user` may
  only read, and requests without a token get a 401.
- Certificate warnings: open `https://<partner-ip>/` once per partner
  server and accept it before using `aas-cli`/the web UI against them,
  otherwise the browser (or `aas-cli` with `verify_tls: true`) will
  reject the connection.

## Structure

```
join.py                 run once: .env, nginx.conf, certificate
docker-compose.yml      full stack: nginx, keycloak, registries, aas-env, web UI
nginx/                  HTTPS proxy template (port 443)
node/                   config + RBAC for your own AAS-Environment
keycloak-registry/      Keycloak realm, registry configs + RBAC (your own)
aas-cli/                CLI to exchange shells/submodels with any server (see its README)
aas/                    example AAS files to upload
excel-to-aasx/, parser/, DPP.json   content tooling (independent of setup)
```

## Troubleshooting

- **A shell doesn't show up for a partner using aas-cli/web UI:** their
  certificate hasn't been accepted yet (see above) — or your server
  isn't reachable from their machine (firewall, wrong port). Confirm
  with `curl -sk https://<your-ip>/shell-descriptors` from their side.
- **My own shell doesn't show up in my own web UI:** check `docker logs
  aas-env` — the registry integration logs every registration attempt
  against your own registry.
- **Realm changed:** it's only imported on Keycloak's first start → run
  `docker compose down -v && docker compose up -d` (this also deletes
  your registry/repo data!).
- **502 from nginx:** Docker network colliding with the LAN? The compose
  network is pinned to `172.30.99.0/24` — adjust if needed.
- **A shell suddenly disappears from the registry even though it's still
  in the repo:** BaSyx quirk (2.0.0-SNAPSHOT): a *rejected* DELETE attempt
  (403, e.g. from a read-only user) still removes the descriptor from the
  registry, and a subsequent PUT does not re-register it — only a CREATE
  does. Workaround: delete the shell as `basyx-admin` and recreate it (or
  re-upload it), and the descriptor will be back.
