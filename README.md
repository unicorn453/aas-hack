# AAS Hack — Team Network

Every machine that clones this repo becomes part of the AAS network:
its own BaSyx server (HTTPS) + web UI, connected via **one shared
registry** and **one shared Keycloak** on the shared host. Everyone sees
everyone's shells; the data stays live on the owner's server.

```
                 SHARED HOST (exactly one per team)
                 ┌────────────────────────────────────┐
                 │ Keycloak     AAS Registry  SM Reg.  │
                 │ (one login)  (shared phone book)    │
                 │        + normal node                │
                 └───▲──────────────▲─────────────────┘
        Token / HTTPS│              │ auto-registered
        ┌────────────┴──┐        ┌──┴────────────┐
        │ NODE Person 2 │◄─────► │ NODE Person 3 │   ... as many as you like
        │ nginx :443    │  reads │ nginx :443    │
        │ env + web-ui  │  live  │ env + web-ui  │
        └───────────────┘        └───────────────┘
```

## Joining (2 commands)

**The shared host** (exactly one person, start this first):

```bash
python3 join.py
docker compose up -d
```

**Everyone else** (use the shared host's IP):

```bash
python3 join.py --shared 192.168.56.219
docker compose up -d
```

Then open `https://<your-own-ip>/` (accept the certificate warning —
self-signed) and log in with `basyx-admin` / `basyx-admin`.

If your IP changes (new day, different network): run `join.py` again and
`docker compose up -d` (restarts the changed containers).

## How it works

- **Uploading your own shells:** Web UI → Upload (AASX/JSON/XML). Your own
  server registers every shell **automatically** in the shared registry
  (BaSyx registry integration) — no script, no cross-registration needed.
- **Seeing others' shells:** The web UI reads the shared registry, gets
  the owner's HTTPS address, and loads the data from there live.
- **One login everywhere:** All servers validate tokens against the same
  Keycloak (shared host). This removes the old problem of "other people's
  shells return 401 because every stack has its own Keycloak."
- **Product made of parts from others:** A new shell simply references
  partners' submodels by ID (ModelReference) — the registry resolves it,
  and the data stays with the partner. Ready-made scripts for this live
  in the sister repo `aas-federation` (`tools/compose_product.py`).

| Service | URL |
|---|---|
| Your own web UI + repo | `https://<your-own-ip>/` |
| Shared registries | `https://<shared-ip>/shell-descriptors`, `/submodel-descriptors` |
| Keycloak (Admin: admin/admin) | `https://<shared-ip>/auth` |

## Security

- Browser traffic runs entirely over **HTTPS** (nginx, self-signed
  certificate per machine). Container-to-shared traffic (token endpoint,
  JWKS, descriptor push) runs over the shared host's LAN HTTP ports
  8082–8084 — acceptable within the team LAN, but not for the internet
  (in that case: use real certificates and route everything over 443).
- Every API requires a Keycloak token: `admin` may write, `user` may only
  read, and requests without a token get a 401. Within the team, everyone
  trusts each other (everyone uses `basyx-admin`) — per-company/per-person
  protection is available via company roles as in the `aas-federation`
  repo (SECURITY.md there).
- Certificate warnings: open `https://<partner-ip>/` once per partner
  server and accept it, otherwise the browser will block reloading the
  data.

## Structure

```
join.py                 run once: .env, nginx.conf, certificate
docker-compose.yml      profiles: node (everyone) + shared (shared host only)
nginx/                  HTTPS proxy template (port 443)
node/                   config + RBAC for your own AAS server
shared/                 Keycloak realm, registry configs + RBAC (shared host)
aas/                    example AAS files to upload
excel-to-aasx/, parser/, DPP.json   content tooling (independent of setup)
```

## Troubleshooting

- **A partner's shell won't load:** their certificate hasn't been
  accepted yet (see above) — or they're offline; the descriptor stays
  in the registry regardless.
- **My own shell doesn't show up for others:** check `docker logs
  aas-env` — the registry integration logs every registration attempt.
  Usually: the shared host isn't reachable, or `join.py` was run with
  the wrong `--shared` IP.
- **Login redirect fails:** the shared host's Keycloak certificate hasn't
  been accepted in the browser yet (open `https://<shared-ip>/auth`).
- **Realm changed:** it's only imported on Keycloak's first start → on
  the shared host run `docker compose down -v && docker compose up -d`
  (this also deletes registry/repo data!).
- **502 from nginx:** Docker network colliding with the LAN? The compose
  network is pinned to `172.30.99.0/24` — adjust if needed.
- **A shell suddenly disappears from the registry even though it's still
  in the repo:** BaSyx quirk (2.0.0-SNAPSHOT): a *rejected* DELETE attempt
  (403, e.g. from a read-only user) still removes the descriptor from the
  registry, and a subsequent PUT does not re-register it — only a CREATE
  does. Workaround: delete the shell as `basyx-admin` and recreate it (or
  re-upload it), and the descriptor will be back.
