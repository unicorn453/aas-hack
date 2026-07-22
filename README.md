# AAS Hack — Team-Netzwerk

Jede Maschine, die dieses Repo klont, wird Teil des AAS-Netzwerks:
eigener BaSyx-Server (HTTPS) + Web UI, verbunden über **eine gemeinsame
Registry** und **ein gemeinsames Keycloak** auf dem Shared-Host. Alle sehen
alle Shells; die Daten bleiben live auf dem Server des Besitzers.

```
                 SHARED-HOST (genau einer im Team)
                 ┌────────────────────────────────────┐
                 │ Keycloak     AAS-Registry  SM-Reg. │
                 │ (ein Login)  (gemeinsames Telefonbuch) │
                 │        + normaler Node             │
                 └───▲──────────────▲─────────────────┘
        Token / HTTPS│              │ auto-registriert
        ┌────────────┴──┐        ┌──┴────────────┐
        │ NODE Person 2 │◄─────► │ NODE Person 3 │   ... beliebig viele
        │ nginx :443    │  liest │ nginx :443    │
        │ env + web-ui  │  live  │ env + web-ui  │
        └───────────────┘        └───────────────┘
```

## Mitmachen (2 Kommandos)

**Der Shared-Host** (genau eine Person, zuerst starten):

```bash
python3 join.py
docker compose up -d
```

**Alle anderen** (IP des Shared-Hosts einsetzen):

```bash
python3 join.py --shared 192.168.56.10
docker compose up -d
```

Danach: `https://<eigene-ip>/` öffnen (Zertifikatswarnung akzeptieren —
selbstsigniert) und mit `basyx-admin` / `basyx-admin` einloggen.

Bei IP-Wechsel (neuer Tag, anderes Netz): `join.py` erneut ausführen und
`docker compose up -d` (startet die geänderten Container neu).

## Wie es funktioniert

- **Eigene Shells hochladen:** Web UI → Upload (AASX/JSON/XML). Der eigene
  Server meldet jede Shell **automatisch** in der gemeinsamen Registry an
  (BaSyx Registry-Integration) — kein Skript, kein Cross-Registrieren.
- **Shells der anderen sehen:** Die Web UI liest die gemeinsame Registry,
  bekommt die HTTPS-Adresse des Besitzers und lädt die Daten dort live.
- **Ein Login überall:** Alle Server prüfen Tokens desselben Keycloak
  (Shared-Host). Das alte Problem „fremde Shells geben 401, weil jeder
  Stack sein eigenes Keycloak hat" ist damit weg.
- **Produkt aus Fremdteilen:** Ein neues Shell referenziert Submodels der
  Partner einfach per ID (ModelReference) — die Registry löst auf, die
  Daten bleiben beim Partner. Fertige Skripte dafür gibt es im
  Schwester-Repo `aas-federation` (`tools/compose_product.py`).

| Dienst | URL |
|---|---|
| Eigene Web UI + eigenes Repo | `https://<eigene-ip>/` |
| Gemeinsame Registries | `https://<shared-ip>/shell-descriptors`, `/submodel-descriptors` |
| Keycloak (Admin: admin/admin) | `https://<shared-ip>/auth` |

## Sicherheit

- Browser-Verkehr komplett über **HTTPS** (nginx, selbstsigniertes Zertifikat
  pro Maschine). Container-zu-Shared-Verkehr (Token-Endpoint, JWKS,
  Descriptor-Push) läuft über LAN-HTTP-Ports 8082–8084 des Shared-Hosts —
  im Team-LAN akzeptabel, fürs Internet nicht (dann: echte Zertifikate und
  alles über 443).
- Jede API verlangt ein Keycloak-Token: `admin` darf schreiben, `user` nur
  lesen, ohne Token gibt es 401. Innerhalb des Teams vertrauen sich alle
  (jeder nutzt `basyx-admin`) — Schutz pro Firma/Person geht mit
  Firmen-Rollen wie im Repo `aas-federation` (SECURITY.md dort).
- Zertifikatswarnungen: einmal pro Partner-Server `https://<partner-ip>/`
  öffnen und akzeptieren, sonst blockt der Browser das Nachladen der Daten.

## Aufbau

```
join.py                 einmalig ausführen: .env, nginx.conf, Zertifikat
docker-compose.yml      Profile: node (jeder) + shared (nur Shared-Host)
nginx/                  HTTPS-Proxy-Template (Port 443)
node/                   Config + RBAC des eigenen AAS-Servers
shared/                 Keycloak-Realm, Registry-Configs + RBAC (Shared-Host)
aas/                    AAS-Beispieldateien zum Hochladen
excel-to-aasx/, parser/, DPP.json   Inhalts-Tooling (unabhängig vom Setup)
```

## Troubleshooting

- **Shell eines Partners lädt nicht:** dessen Zertifikat noch nicht
  akzeptiert (siehe oben) — oder er ist offline; der Descriptor bleibt
  dann trotzdem in der Registry stehen.
- **Eigene Shell erscheint nicht bei anderen:** `docker logs aas-env` —
  die Registry-Integration loggt jeden Anmeldeversuch. Meist: Shared-Host
  nicht erreichbar oder `join.py` mit falscher `--shared`-IP gelaufen.
- **Login-Redirect schlägt fehl:** Keycloak-Zertifikat des Shared-Hosts
  im Browser noch nicht akzeptiert (`https://<shared-ip>/auth` öffnen).
- **Realm geändert:** wird nur beim ersten Keycloak-Start importiert →
  auf dem Shared-Host `docker compose down -v && docker compose up -d`
  (löscht auch Registry-/Repo-Daten!).
- **502 vom nginx:** Docker-Netz kollidiert mit dem LAN? Das Compose-Netz
  ist auf `172.30.99.0/24` gepinnt — ggf. anpassen.
- **Shell plötzlich nicht mehr in der Registry, obwohl sie im Repo liegt:**
  BaSyx-Eigenheit (2.0.0-SNAPSHOT): ein *abgelehnter* DELETE-Versuch (403,
  z. B. durch einen Nur-Lese-User) entfernt den Descriptor trotzdem aus der
  Registry, und ein PUT meldet ihn nicht neu an — nur ein CREATE tut das.
  Abhilfe: Shell als `basyx-admin` löschen und neu anlegen (bzw. neu
  hochladen), dann ist der Descriptor wieder da.
