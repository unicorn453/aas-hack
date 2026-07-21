"""
Cross-registration: register your own shells in a partner's registry so
the partner finds them in their own registry and reads the data LIVE from
our server (no copy).

How it works:
  - The ready-made descriptors are read from our OWN registry (aas-env
    already put them there thanks to registryintegration; the endpoint
    hrefs point at our external address thanks to basyx.externalurl) and
    forwarded 1:1 to the partner registry.
  - For each shell the descriptors of all referenced submodels are also
    registered in the partner's submodel registry.
  - --deregister removes the entries from the partner registry again
    (e.g. before shutting down your own stack).

Prerequisites:
  - The partner can reach our IP (same LAN).
  - We have valid credentials for the partner's Keycloak (write access to
    their registry).
  - The RBAC rules of OUR server allow the partner to read — otherwise
    they find the shell but get 401/403 when fetching it.

Run:
    # register all own shells at the partner
    .venv-scripts/bin/python3 register_remote.py --partner-url https://<partner-ip>

    # only one specific shell
    .venv-scripts/bin/python3 register_remote.py --partner-url https://<partner-ip> --aas-id <aas-id>

    # remove again
    .venv-scripts/bin/python3 register_remote.py --partner-url https://<partner-ip> --deregister
"""

import argparse

import requests

from aas_client import (TokenPool, Server, add_credential_args,
                        credentials_from_args, submodel_ids_of)


def own_shell_ids(me: Server, my_url: str) -> list[str]:
    """
    Ids of all shells in our own registry whose endpoint points at our own
    server. Filters out foreign descriptors that others cross-registered
    with us — we do not forward those.
    """
    ids = []
    for descriptor in me.list_shell_descriptors():
        try:
            href = descriptor["endpoints"][0]["protocolInformation"]["href"]
        except (KeyError, IndexError):
            continue
        if href.startswith(my_url):
            ids.append(descriptor["id"])
    return ids


def register(me: Server, partner: Server, aas_id: str) -> None:
    """Register the descriptor of one shell + its submodels at the partner."""
    descriptor = me.get_shell_descriptor(aas_id)
    status = partner.upsert_shell_descriptor(descriptor)
    print(f"[shell-descriptor] {descriptor.get('idShort', aas_id)!r} {status}")

    # Determine the submodel ids from the shell in our own repository
    shell = me.download_shell(aas_id)
    for sm_id in submodel_ids_of(shell):
        try:
            sm_descriptor = me.get_submodel_descriptor(sm_id)
        except requests.HTTPError:
            print(f"[submodel-descriptor] {sm_id} not in own registry, skipped")
            continue
        status = partner.upsert_submodel_descriptor(sm_descriptor)
        print(f"[submodel-descriptor] {sm_descriptor.get('idShort', sm_id)!r} {status}")


def deregister(me: Server, partner: Server, aas_id: str) -> None:
    """Remove the descriptor of one shell + its submodels at the partner."""
    # Determine the submodel ids from our own shell while it still exists;
    # if the shell is gone locally, only delete the shell descriptor.
    sm_ids: list[str] = []
    try:
        sm_ids = submodel_ids_of(me.download_shell(aas_id))
    except requests.HTTPError:
        pass

    try:
        partner.delete_shell_descriptor(aas_id)
        print(f"[shell-descriptor] {aas_id} removed at partner")
    except requests.HTTPError as e:
        print(f"[shell-descriptor] {aas_id} not removed ({e.response.status_code})")

    for sm_id in sm_ids:
        try:
            partner.delete_submodel_descriptor(sm_id)
            print(f"[submodel-descriptor] {sm_id} removed")
        except requests.HTTPError as e:
            print(f"[submodel-descriptor] {sm_id} not removed ({e.response.status_code})")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--partner-url", required=True,
                        help="base URL of the partner registry, e.g. https://<partner-ip>")
    parser.add_argument("--my-url", default="https://192.168.56.76",
                        help="base URL of your own server")
    parser.add_argument("--aas-id", default=None,
                        help="only this shell (default: all own shells)")
    parser.add_argument("--deregister", action="store_true",
                        help="remove the descriptors at the partner instead of registering")
    add_credential_args(parser, ("my", "partner"))
    args = parser.parse_args()

    # Register credentials per host — the pool picks the token for every
    # request based on the URL host
    pool = TokenPool()
    pool.add_host(args.my_url, credentials_from_args(args, "my"))
    pool.add_host(args.partner_url, credentials_from_args(args, "partner"))

    me = Server(args.my_url, pool)
    partner = Server(args.partner_url, pool)

    if args.aas_id:
        aas_ids = [args.aas_id]
    else:
        aas_ids = own_shell_ids(me, args.my_url)
        print(f"[registry] {len(aas_ids)} own shell(s) found")

    for aas_id in aas_ids:
        action = "Deregistering" if args.deregister else "Registering"
        print(f"\n=== {action} {aas_id} ===")
        if args.deregister:
            deregister(me, partner, aas_id)
        else:
            register(me, partner, aas_id)


if __name__ == "__main__":
    main()
