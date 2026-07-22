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

Usage:
    python3 setup_local_ip.py
    python3 setup_local_ip.py --ip 192.168.1.42   # override auto-detection
"""

import argparse
import shutil
import socket
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

TEMPLATES = [
    REPO_ROOT / "nginx" / "nginx.conf.template",
    REPO_ROOT / "basyx-infra.yml" / "basyx-infra.yml.template",
    REPO_ROOT / "_files" / "aas-env.properties" / "application.properties.template",
    REPO_ROOT / "_files" / "keycloak" / "realm-basyx.json.template",
]

PLACEHOLDER = "__HOST_ADDRESS__"


def detect_local_ip():
    """Finds the IP of the interface used to reach the LAN, without depending
    on any particular interface name (works the same on Mac/Linux/Windows)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def write_env(ip):
    env_path = REPO_ROOT / ".env"
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    lines = [l for l in lines if not l.startswith("HOST_ADDRESS=")]
    lines.append(f"HOST_ADDRESS={ip}")
    env_path.write_text("\n".join(lines) + "\n")
    print(f"[.env] HOST_ADDRESS={ip}")


def render_templates(ip):
    for template_path in TEMPLATES:
        output_path = template_path.with_suffix("")  # drop ".template"
        # If `docker compose up` ran before this script, Docker auto-created
        # the missing bind-mount source as an empty DIRECTORY - remove it,
        # otherwise write_text() fails with IsADirectoryError forever.
        if output_path.is_dir():
            shutil.rmtree(output_path)
            print(f"[render] removed stray directory {output_path.relative_to(REPO_ROOT)} (created by docker)")
        content = template_path.read_text().replace(PLACEHOLDER, ip)
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
    args = parser.parse_args()

    ip = args.ip or detect_local_ip()
    print(f"Using IP: {ip}")

    write_env(ip)
    render_templates(ip)
    ensure_cert(ip)

    print("\nDone. Run `docker compose up -d` (or `podman compose up -d`) to start the stack.")


if __name__ == "__main__":
    main()
