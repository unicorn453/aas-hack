"""
Makes this repo runnable on your own machine instead of whoever committed it last.

docker-compose.yml already reads HOST_ADDRESS from .env, but a few files that get
bind-mounted into containers as-is (nginx, Keycloak realm, aas-env properties,
aas-web-ui infra config) don't support that kind of substitution - they need the
real address baked in as plain text. This script detects your machine's LAN IP,
writes it to .env, and renders those files from their *.template counterparts.

Run this once after cloning, and again any time your IP changes (new day at the
venue, different network, etc). Safe to rerun - it only touches generated files,
never the .template sources.

The stack can either run its own Keycloak (default) or use the Keycloak of
another team member's stack, so the whole team shares one identity provider
and tokens are valid on every stack:

Usage:
    python3 setup_local_ip.py
    python3 setup_local_ip.py --ip 192.168.1.42   # override auto-detection
    python3 setup_local_ip.py --keycloak-address 192.168.56.76   # use team Keycloak
"""

import argparse
import socket
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

TEMPLATES = [
    REPO_ROOT / "nginx" / "nginx.conf.template",
    REPO_ROOT / "basyx-infra.yml" / "basyx-infra.yml.template",
    REPO_ROOT / "_files" / "aas-env.properties" / "application.properties.template",
    REPO_ROOT / "_files" / "keycloak" / "realm-basyx.json.template",
    REPO_ROOT / "_files" / "aas-registry.yml.template",
    REPO_ROOT / "_files" / "sm-registry.yml.template",
]

PLACEHOLDER = "__HOST_ADDRESS__"
# Keycloak base URL as seen from inside the containers (token endpoints,
# jwk-set-uri) and the upstream nginx proxies /auth to.
KC_BASE_PLACEHOLDER = "__KEYCLOAK_BASE__"
KC_UPSTREAM_PLACEHOLDER = "__KEYCLOAK_UPSTREAM__"


def detect_local_ip():
    """Finds the IP of the interface used to reach the LAN, without depending
    on any particular interface name (works the same on Mac/Linux/Windows)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def write_env(ip, keycloak_address, hosts_keycloak):
    env_path = REPO_ROOT / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    managed = ("HOST_ADDRESS=", "KEYCLOAK_ADDRESS=", "COMPOSE_PROFILES=")
    lines = [l for l in lines if not l.startswith(managed)]
    lines.append(f"HOST_ADDRESS={ip}")
    lines.append(f"KEYCLOAK_ADDRESS={keycloak_address}")
    # The keycloak + keycloak-db containers only start on the machine that
    # hosts the (team) Keycloak.
    lines.append(f"COMPOSE_PROFILES={'keycloak' if hosts_keycloak else ''}")
    env_path.write_text("\n".join(lines) + "\n")
    print(f"[.env] HOST_ADDRESS={ip}")
    print(f"[.env] KEYCLOAK_ADDRESS={keycloak_address}"
          + ("" if hosts_keycloak else " (remote — own keycloak containers stay off)"))


def render_templates(ip, hosts_keycloak, keycloak_address):
    if hosts_keycloak:
        # Local Keycloak container, reachable via the compose network
        kc_base = "http://keycloak:8080/auth"
        kc_upstream = "keycloak:8080"
    else:
        # Team Keycloak on another machine, reachable via its published
        # plain-HTTP port 8084 (avoids self-signed-cert issues in Java)
        kc_base = f"http://{keycloak_address}:8084/auth"
        kc_upstream = f"{keycloak_address}:8084"

    for template_path in TEMPLATES:
        output_path = template_path.with_suffix("")  # drop ".template"
        content = (template_path.read_text()
                   .replace(PLACEHOLDER, ip)
                   .replace(KC_BASE_PLACEHOLDER, kc_base)
                   .replace(KC_UPSTREAM_PLACEHOLDER, kc_upstream))
        output_path.write_text(content)
        print(f"[render] {template_path.relative_to(REPO_ROOT)} -> {output_path.relative_to(REPO_ROOT)}")


def cert_matches_ip(cert_path, ip):
    try:
        out = subprocess.run(
            ["openssl", "x509", "-noout", "-ext", "subjectAltName", "-in", str(cert_path)],
            capture_output=True, text=True, check=True,
        ).stdout
        return ip in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def ensure_cert(ip):
    certs_dir = REPO_ROOT / "certs"
    certs_dir.mkdir(exist_ok=True)
    crt, key = certs_dir / "server.crt", certs_dir / "server.key"

    if crt.exists() and key.exists() and cert_matches_ip(crt, ip):
        print(f"[certs] already valid for {ip}, skipping")
        return

    try:
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:4096", "-sha256", "-days", "3650", "-nodes",
                "-keyout", str(key), "-out", str(crt),
                "-subj", f"/CN={ip}",
                "-addext", f"subjectAltName=IP:{ip}",
            ],
            check=True, capture_output=True,
        )
        print(f"[certs] generated certs/server.crt for {ip}")
    except FileNotFoundError:
        print("[certs] openssl not found on PATH - generate certs/server.crt manually, see README")
    except subprocess.CalledProcessError as e:
        print(f"[certs] openssl failed: {e.stderr.decode().strip()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ip", default=None, help="Use this IP instead of auto-detecting it")
    parser.add_argument("--keycloak-address", default=None,
                        help="IP of the team member hosting the shared Keycloak "
                             "(default: this machine hosts its own Keycloak)")
    args = parser.parse_args()

    ip = args.ip or detect_local_ip()
    keycloak_address = args.keycloak_address or ip
    hosts_keycloak = keycloak_address == ip
    print(f"Using IP: {ip}")
    print(f"Keycloak: {'own (this machine)' if hosts_keycloak else keycloak_address}")

    write_env(ip, keycloak_address, hosts_keycloak)
    render_templates(ip, hosts_keycloak, keycloak_address)
    ensure_cert(ip)

    print("\nDone. Run `docker compose up -d` (or `podman compose up -d`) to start the stack.")


if __name__ == "__main__":
    main()
