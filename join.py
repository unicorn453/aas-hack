#!/usr/bin/env python3
"""
Macht diese Maschine zu einem eigenständigen AAS-Server. Einmal nach dem
Klonen ausführen (und erneut, wenn sich die eigene IP ändert).

    python3 join.py

Jede Maschine betreibt ihren kompletten eigenen Stack: eigenes Keycloak,
eigene AAS-/Submodel-Registry, eigenes AAS-Environment + Web UI. Es gibt
keine gemeinsame Instanz und keine Abhängigkeit von einer anderen Maschine
-- Datenaustausch mit Teammitgliedern/Partnern läuft über aas-cli
(siehe aas-cli/README.md).

Das Skript:
  1. erkennt die eigene LAN-IP (überschreibbar mit --ip),
  2. schreibt .env (eigene IP),
  3. erzeugt nginx/nginx.conf aus dem Template,
  4. erzeugt ein selbstsigniertes TLS-Zertifikat für die eigene IP.

Danach:  docker compose up -d
"""

import argparse
import socket
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def detect_local_ip() -> str:
    """IP des Interfaces, über das das LAN erreicht wird (kein Traffic nötig)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def write_env(my_ip: str) -> None:
    (REPO_ROOT / ".env").write_text(
        f"""# Generiert von join.py — nicht committen, bei IP-Wechsel join.py neu ausführen.
HOST_ADDRESS={my_ip}
""")
    print(f"[.env]   HOST_ADDRESS={my_ip}")


def render_nginx(my_ip: str) -> None:
    template = (REPO_ROOT / "nginx" / "nginx.conf.template").read_text()
    conf = template.replace("__HOST_ADDRESS__", my_ip)
    (REPO_ROOT / "nginx" / "nginx.conf").write_text(conf)
    print("[nginx]  nginx/nginx.conf erzeugt")


def generate_cert(my_ip: str) -> None:
    certs = REPO_ROOT / "certs"
    certs.mkdir(exist_ok=True)
    crt, key = certs / "server.crt", certs / "server.key"
    marker = certs / ".for-ip"
    if crt.exists() and marker.exists() and marker.read_text().strip() == my_ip:
        print(f"[certs]  Zertifikat für {my_ip} existiert bereits")
        return
    try:
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:4096", "-sha256",
             "-days", "3650", "-nodes",
             "-keyout", str(key), "-out", str(crt),
             "-subj", f"/CN={my_ip}",
             "-addext", f"subjectAltName=IP:{my_ip}"],
            check=True, capture_output=True)
        marker.write_text(my_ip + "\n")
        print(f"[certs]  selbstsigniertes Zertifikat für {my_ip} erzeugt")
    except FileNotFoundError:
        sys.exit("FEHLER: openssl nicht gefunden — bitte installieren und "
                 "join.py erneut ausführen.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"FEHLER bei der Zertifikatserzeugung:\n{e.stderr.decode()}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ip", default=None,
                        help="eigene IP (Default: automatisch erkannt)")
    args = parser.parse_args()

    my_ip = args.ip or detect_local_ip()

    write_env(my_ip)
    render_nginx(my_ip)
    generate_cert(my_ip)

    print(f"""
Fertig. Jetzt starten:

    docker compose up -d

Web UI:    https://{my_ip}/          (Login: basyx-admin / basyx-admin)
Keycloak:  https://{my_ip}/auth      (Admin-Konsole: admin / admin)

Hinweis: Selbstsigniertes Zertifikat — beim ersten Besuch im Browser
akzeptieren. Um mit Teammitgliedern/Partnern Shells auszutauschen,
aas-cli benutzen (siehe aas-cli/README.md) und einmal
https://<partner-ip>/ öffnen, um dessen Zertifikat zu akzeptieren.""")


if __name__ == "__main__":
    main()
