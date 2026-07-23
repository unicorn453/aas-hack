# aas-cli

Command-line client for BaSyx AAS servers. Every server you can reach
(your own node from [join.py](../join.py), a teammate's, or an external
partner's) is a named entry in a config file; every command takes
`--server <name>` to pick which one to talk to and a flag for what to do
(`list`, `upload`, `download`, `delete`). Authentication (Keycloak
username/password grant) and BaSyx's base64url ID-encoding are handled
for you.

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
