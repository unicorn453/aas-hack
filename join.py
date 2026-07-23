#!/usr/bin/env python3
"""
Macht diese Maschine zu einem Teil des AAS-Netzwerks. Einmal nach dem
Klonen ausführen (und erneut, wenn sich die eigene IP ändert).

Zwei Rollen:

  Shared-Host  (genau EINER im Team — betreibt Keycloak + gemeinsame Registries
                UND ist gleichzeitig normaler Node):
      python3 join.py

  Node         (alle anderen — eigener AAS-Server + Web UI, angebunden an
                den Shared-Host):
      python3 join.py --shared 192.168.56.10

Das Skript:
  1. erkennt die eigene LAN-IP (überschreibbar mit --ip),
  2. schreibt .env (Rolle, IPs, interne URLs),
  3. erzeugt nginx/nginx.conf aus dem Template (Shared-Host bekommt
     zusätzlich /auth und die Registry-Routen),
  4. erzeugt ein selbstsigniertes TLS-Zertifikat für die eigene IP.

Danach:  docker compose up -d
"""

import argparse
import socket
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# Routen, die nur auf dem Shared-Host existieren (Keycloak + gemeinsame
# Registries laufen nur dort). Auf normalen Nodes zeigt die Web UI direkt
# auf https://<shared-ip>/... — diese Locations werden dort nicht gebraucht
# und würden nginx wegen unbekannter Upstreams am Start hindern.
SHARED_LOCATIONS = """
    # --- nur Shared-Host: gemeinsame AAS-Registry ---
    # CORS wird hier von nginx gesetzt, nicht vom Registry-Image: die
    # basyx.cors.*-Konfiguration in shared/aas-registry.yml wird von
    # eclipsebasyx/aas-registry-log-mongodb (2.0.0-SNAPSHOT) nicht auf die
    # Responses angewendet, weder bei 200 noch bei 401 -- Browser einer
    # anderen Node-IP blockieren die Registry-Antworten dadurch per CORS.
    location /shell-descriptors {
        proxy_pass         http://aas-registry:8080;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
        if ($request_method = OPTIONS) {
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
            add_header 'Content-Length' 0;
            return 204;
        }
    }

    # --- nur Shared-Host: gemeinsame Submodel-Registry ---
    location /submodel-descriptors {
        proxy_pass         http://submodel-registry:8080;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
        if ($request_method = OPTIONS) {
            add_header 'Access-Control-Allow-Origin' '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept' always;
            add_header 'Content-Length' 0;
            return 204;
        }
    }

    # --- nur Shared-Host: gemeinsames Keycloak ---
    location = /auth {
        return 301 /auth/;
    }

    location /auth/ {
        proxy_pass            http://keycloak:8080/auth/;
        proxy_set_header      Host               $host;
        proxy_set_header      X-Forwarded-For    $proxy_add_x_forwarded_for;
        proxy_set_header      X-Forwarded-Proto  $scheme;
        proxy_set_header      X-Forwarded-Port   443;
        proxy_buffer_size     128k;
        proxy_buffers         4 256k;
        proxy_busy_buffers_size 256k;
    }
"""


def detect_local_ip() -> str:
    """IP des Interfaces, über das das LAN erreicht wird (kein Traffic nötig)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def write_env(my_ip: str, shared_ip: str, is_shared_host: bool) -> None:
    if is_shared_host:
        # Eigene Container erreichen die Shared-Dienste über das Compose-Netz
        kc_internal = "http://keycloak:8080/auth"
        aas_reg_internal = "http://aas-registry:8080"
        sm_reg_internal = "http://submodel-registry:8080"
        profiles = "node,shared"
    else:
        # Shared-Dienste laufen auf einer anderen Maschine — über deren
        # veröffentlichte HTTP-Ports (LAN-intern; Browser gehen über HTTPS/443)
        kc_internal = f"http://{shared_ip}:8084/auth"
        aas_reg_internal = f"http://{shared_ip}:8082"
        sm_reg_internal = f"http://{shared_ip}:8083"
        profiles = "node"

    (REPO_ROOT / ".env").write_text(
        f"""# Generiert von join.py — nicht committen, bei IP-Wechsel join.py neu ausführen.
HOST_ADDRESS={my_ip}
SHARED_ADDRESS={shared_ip}
COMPOSE_PROFILES={profiles}
KC_INTERNAL={kc_internal}
AAS_REGISTRY_INTERNAL={aas_reg_internal}
SM_REGISTRY_INTERNAL={sm_reg_internal}
""")
    role = "Shared-Host (Keycloak + Registries + eigener Node)" if is_shared_host else f"Node (Shared-Host: {shared_ip})"
    print(f"[.env]   HOST_ADDRESS={my_ip}  —  Rolle: {role}")


def render_nginx(my_ip: str, is_shared_host: bool) -> None:
    template = (REPO_ROOT / "nginx" / "nginx.conf.template").read_text()
    conf = (template
            .replace("__HOST_ADDRESS__", my_ip)
            .replace("__SHARED_LOCATIONS__", SHARED_LOCATIONS if is_shared_host else ""))
    (REPO_ROOT / "nginx" / "nginx.conf").write_text(conf)
    print(f"[nginx]  nginx/nginx.conf erzeugt"
          + (" (inkl. /auth + Registry-Routen)" if is_shared_host else ""))


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
    parser.add_argument("--shared", metavar="IP", default=None,
                        help="IP des Shared-Hosts. Weglassen = ICH bin der Shared-Host.")
    parser.add_argument("--ip", default=None,
                        help="eigene IP (Default: automatisch erkannt)")
    args = parser.parse_args()

    my_ip = args.ip or detect_local_ip()
    is_shared_host = args.shared is None or args.shared == my_ip
    shared_ip = my_ip if is_shared_host else args.shared

    write_env(my_ip, shared_ip, is_shared_host)
    render_nginx(my_ip, is_shared_host)
    generate_cert(my_ip)

    print(f"""
Fertig. Jetzt starten:

    docker compose up -d

Web UI:    https://{my_ip}/          (Login: basyx-admin / basyx-admin)
Keycloak:  https://{shared_ip}/auth  (Admin-Konsole: admin / admin)

Hinweis: Selbstsigniertes Zertifikat — beim ersten Besuch im Browser
akzeptieren. Damit Shells von Partnern in der UI laden, einmal
https://<partner-ip>/ öffnen und auch deren Zertifikat akzeptieren.""")


if __name__ == "__main__":
    main()
