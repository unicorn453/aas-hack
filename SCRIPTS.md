# Python scripts: find, copy, and cross-register shells

All scripts run with the project venv:

```bash
python3 -m venv .venv-scripts
.venv-scripts/bin/pip install aas-python-http-client requests
```

| File | Purpose |
|---|---|
| `aas_client.py` | Shared building blocks: `TokenPool` (one token per host), `Server` (registry + repository of one stack) |
| `find_and_download_shell.py` | Demo of the open-source client `aas-python-http-client` against **one** stack: list descriptors, resolve endpoint, download shell |
| `copy_shell.py` | Copy shells **including submodels** from a (partner) registry to your own server (snapshot) |
| `register_remote.py` | **Cross-register** your own shells in a partner's registry so they read your data live (no copy); `--deregister` removes the entries again |

## Two ways to share data

1. **Copying** (`copy_shell.py`): shell + submodels are physically
   transferred to the partner. Keeps working when the source goes offline —
   but the copy goes stale.
2. **Cross-registration** (`register_remote.py`): only a *descriptor* is
   registered at the partner, with an endpoint `href` pointing at our
   server. The partner finds the shell in their own registry and reads the
   data **live** from us on every access. A registry stores no data, only
   pointers — like DNS.

## The cross-registry problem (token ≠ host)

Every stack in the team runs its **own Keycloak**, and every BaSyx server
only accepts tokens signed by *its* Keycloak
(`spring.security.oauth2.resourceserver.jwt.jwk-set-uri` in the aas-env
properties). A token from a foreign Keycloak already fails the signature
check — **before** any RBAC rules are evaluated. Granting read permissions
in the RBAC file does not help then.

This is exactly what bites you with cross-registration:

```
partner script                                       .
   │  1. GET /shell-descriptors        token B ✔     .
   ▼                                                 .
registry of server B  ──►  descriptor                .
                           href = https://A/shells/…
   │  2. GET on the href                             .
   ▼                                                 .
server A   ◄── token B ✘ 401  /  token A ✔ 200       .
```

The descriptor comes from server B (needs token B), but its `href` points
at server A — that request needs a token from Keycloak A. A client that
stubbornly uses *one* token for everything gets a 401 when resolving the
`href`, even though "the permissions are all there".

**Hence the clean rule: the token must always match the host of the URL
being requested.**

## Implementation: `TokenPool` in `aas_client.py`

The `TokenPool` is given each stack's base URL and Keycloak credentials
(`add_host`). On every request it picks the matching token based on the
**URL host**, fetches it on demand (password grant), caches it until
shortly before expiry, and retries a request once with a fresh token after
a 401. If an `href` points at a host without registered credentials, you
get a clear error instead of a bare 401:

```
No credentials registered for host '10.0.0.99' (known: 192.168.56.76).
The URL probably comes from a cross-registered descriptor — add
credentials for this host via add_host() or --extra-host.
```

Both scripts automatically add their two main hosts to the pool
(`--source-*`/`--target-*` and `--my-*`/`--partner-*` respectively). For
descriptors whose `href` points at a **third** host there is
`--extra-host`:

```bash
# The partner registry also contains shells cross-registered from host C:
.venv-scripts/bin/python3 copy_shell.py \
  --source-url https://<partner-ip> \
  --extra-host https://<host-c> basyx-user basyx-user
```

## Typical invocations

```bash
# Copy all of the partner's shells to my stack (read-only account on their side)
.venv-scripts/bin/python3 copy_shell.py \
  --source-url https://<partner-ip> \
  --source-username basyx-user --source-password basyx-user

# Register my shells at the partner (live sharing) / remove them again
.venv-scripts/bin/python3 register_remote.py --partner-url https://<partner-ip>
.venv-scripts/bin/python3 register_remote.py --partner-url https://<partner-ip> --deregister
```

## Read access for partners

For a partner to fetch our live-shared data they need an account in **our**
Keycloak. The realm ships with:

- `basyx-admin` / `basyx-admin` — full access (role `admin`)
- `basyx-user` / `basyx-user` — read-only (role `user`, READ on everything
  per `_files/rules/aas_env_rbac_rules.json`)

So hand out `basyx-user` to partners. Note that the partner's **browser
UI** still cannot open cross-registered shells (the UI always gets its
token from its own Keycloak — the issuer problem above); either they use
our web UI (`https://<our-ip>/`, login `basyx-user`) or the team runs a
shared Keycloak.
