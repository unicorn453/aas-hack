# aas-cli

Command-line client for BaSyx AAS servers. Every server you can reach
(your own node from [join.py](../join.py), a teammate's, or an external
partner's) is a named entry in a config file; every command takes
`--server <name>` to pick which one to talk to and a flag for what to do
(`list`, `upload`, `download`, `delete`). Authentication and BaSyx's
base64url ID-encoding are handled for you. Two Keycloak grant types are
supported per server: `password` (default -- a real user logs in) and
`client_credentials` (a service-account client with no end user, common
for external partners that don't want to hand out personal logins).

## Install

```bash
cd aas-cli
pip install -e .
```

## Configure

Generate a `servers.yaml` with a `local` entry from this repo's own
`.env` (written by `../join.py`):

```bash
aas-cli init            # writes ./servers.yaml
```

Then add any other servers (teammates', partners') by hand -- see
[servers.example.yaml](servers.example.yaml) for the shape. Config is
looked up in this order: `--config PATH`, `$AAS_CLI_CONFIG`,
`./aas-cli.yaml`, `./servers.yaml`, `~/.config/aas-cli/servers.yaml`.

```bash
aas-cli servers          # sanity-check what's configured
```

## Use

```bash
# list what's on a server
aas-cli list --server local --type shell
aas-cli list --server local --type shell --ids-only
aas-cli list --server local --type shell --registry   # via the shared registry instead

# upload an environment file (AASX / JSON / XML) -- same as the web UI's Upload button
aas-cli upload --server local --file ../aas/aas.json

# download a single shell/submodel, or the whole environment if --id is omitted
aas-cli download --server partner1 --type shell --id "https://acplt.org/Simple_AAS" --out shell.json
aas-cli download --server local --out backup.json

# delete a shell or submodel
aas-cli delete --server local --type shell --id "https://acplt.org/Simple_AAS"
```

Every server entry is independent -- `local` can use this team's shared
Keycloak while `external` points at a completely different partner's
auth, per [servers.example.yaml](servers.example.yaml).

## Example use cases

**Upload your own shell and confirm it registered.** This repo's `aas-env`
auto-registers every shell/submodel you upload in the shared registry --
no extra step needed.

```bash
aas-cli upload --server local --file ../aas/aas.json
aas-cli list --server local --type shell --registry --ids-only
```

**Back up your whole environment.** `download` without `--id` serializes
everything (all shells, submodels, concept descriptions) into one file.

```bash
aas-cli download --server local --out backup-$(date +%F).json
```

**See what a teammate or partner has, without touching your own data.**
Point `--server` at their entry instead of `local` -- your own repository
and Keycloak are untouched.

```bash
aas-cli list --server mein-partner --type shell
```

If the shell doesn't show up in the *web UI* even though `aas-cli` sees
it fine, that's very likely CORS or an untrusted certificate in the
browser, not a data problem -- see the main [README](../README.md#troubleshooting).

**Send them a shell.** `upload` always writes to whatever `--server` you
pass -- there's nothing "local" about it, the file just travels to
whichever repository that server entry points at.

```bash
aas-cli upload --server mein-partner --file ../aas/EGU_50_IL_M_B.aasx
```

**Pull a specific shell from a partner, as AASX.** Useful when you want
to reuse or archive one of their shells rather than mirroring everything.

```bash
aas-cli download --server mein-partner --type shell \
  --id "https://admin-shell.io/idta/aas/ProductA/1/0" \
  --format aasx --out productA.aasx
```

**Connect to an external partner with their own Keycloak (password
grant).** Same shape as `local`, just pointed at their infrastructure --
see the `external` entry in
[servers.example.yaml](servers.example.yaml).

```yaml
partner-with-users:
  url: https://partner.example.org
  verify_tls: true
  keycloak:
    url: https://auth.partner.example.org
    realm: partner-realm
    client_id: partner-client
  username: my-user-there
  password_env: PARTNER_PASSWORD
```

**Connect to a partner whose client is a service account (no personal
login).** Set `grant_type: client_credentials` -- then `username` /
`password` / `password_env` aren't needed at all, only `client_id` +
`client_secret`.

```yaml
partner-service-account:
  url: http://192.168.56.212:8081
  registry_url: http://192.168.56.212:8081
  verify_tls: false
  keycloak:
    url: https://192.168.56.212:9443
    realm: BaSyx            # realm names are case-sensitive
    client_id: basyx-admin
    client_secret: "..."
    grant_type: client_credentials
```

```bash
aas-cli list --server partner-service-account --type shell
```

**Delete something you uploaded by mistake.**

```bash
aas-cli delete --server local --type shell --id "https://acplt.org/Simple_AAS"
```

## How it maps to the BaSyx REST API

| Command                 | Endpoint                                          |
| ------------------------ | -------------------------------------------------- |
| `list --type shell`      | `GET /shells` (or `/submodels`, `/concept-descriptions`) |
| `list --registry`        | `GET <registry_url>/shell-descriptors` (or `/submodel-descriptors`) |
| `upload`                 | `POST /upload` (multipart, bulk AASX/JSON/XML import) |
| `download` (with `--id`) | `GET /serialization?aasIds=...\|submodelIds=...`  |
| `download` (no `--id`)   | `GET /serialization` (whole environment)          |
| `delete`                 | `DELETE /shells/{base64url-id}` (or `/submodels/{...}`) |

IDs in URL paths are UTF8-BASE64-URL-encoded per the BaSyx API spec --
`aas_cli/encoding.py` handles that, you always pass the plain ID
(e.g. `https://acplt.org/Simple_AAS`) on the command line.
