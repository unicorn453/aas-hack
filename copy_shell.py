"""
Copy shells including all referenced submodels from a (partner) registry
to your own server.

Flow per shell:
  1. Source: fetch the descriptor from the registry, resolve the endpoint,
     load the shell
  2. Source: load every submodel referenced in the "submodels" field
     (endpoint preferably resolved via the submodel registry)
  3. Target: upload shell + submodels via POST; on 409 (already exists)
     update via PUT instead

Registration in the target registry happens automatically because aas-env
is configured with registryintegration — we only upload to the repository.

Tokens are picked per host automatically (see aas_client.py / SCRIPTS.md).
If an endpoint href points at a third host (cross-registered descriptor),
pass its credentials via --extra-host.

Run (everything from the partner registry to your own server):
    .venv-scripts/bin/python3 copy_shell.py --source-url https://<partner-ip>
    .venv-scripts/bin/python3 copy_shell.py --source-url https://<partner-ip> --aas-id https://acplt.org/Simple_AAS
"""

import argparse

import requests

from aas_client import (Credentials, TokenPool, Server, add_credential_args,
                        credentials_from_args, submodel_ids_of)


def copy_shell(source: Server, target: Server, aas_id: str) -> None:
    """Copy one shell including all its submodels from source to target."""
    shell = source.download_shell(aas_id)
    print(f"[shell] {shell.get('idShort', aas_id)!r} loaded from {source.base_url}")

    status = target.upload_shell(shell)
    print(f"[shell] {status} on {target.base_url}")

    for sm_id in submodel_ids_of(shell):
        try:
            submodel = source.download_submodel(sm_id)
        except requests.HTTPError as e:
            # Referenced submodel does not exist on the source -> skip
            print(f"[submodel] {sm_id} not loadable ({e.response.status_code}), skipped")
            continue
        status = target.upload_submodel(submodel)
        print(f"[submodel] {submodel.get('idShort', sm_id)!r} {status}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-url", required=True,
                        help="base URL of the source, e.g. https://<partner-ip>")
    parser.add_argument("--target-url", default="https://192.168.56.76",
                        help="base URL of your own server")
    parser.add_argument("--aas-id", default=None,
                        help="copy only this shell (default: all from the source registry)")
    add_credential_args(parser, ("source", "target"))
    args = parser.parse_args()

    # Register credentials per host — the pool picks the token for every
    # request based on the URL host
    pool = TokenPool()
    pool.add_host(args.source_url, credentials_from_args(args, "source"))
    pool.add_host(args.target_url, credentials_from_args(args, "target"))
    for url, user, password in args.extra_host:
        pool.add_host(url, Credentials(username=user, password=password))

    source = Server(args.source_url, pool)
    target = Server(args.target_url, pool)

    if args.aas_id:
        aas_ids = [args.aas_id]
    else:
        aas_ids = [d["id"] for d in source.list_shell_descriptors()]
        print(f"[registry] {len(aas_ids)} shell(s) in the source registry")

    for aas_id in aas_ids:
        print(f"\n=== Copying {aas_id} ===")
        copy_shell(source, target, aas_id)


if __name__ == "__main__":
    main()
