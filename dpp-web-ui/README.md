# Schunk DPP Monitor

A standalone React, TypeScript and Vite interface for the Schunk PGN+ P 64-1
Digital Product Passport. It runs beside the existing BaSyx Web UI and does not
replace it.

The public asset and five static DPP submodels are loaded anonymously through
`dpp-public-api`. Keycloak Authorization Code + PKCE is initialized in `check-sso`
mode, so opening the page never redirects an anonymous visitor. Only a token
with the Keycloak realm role `admin` starts protected TimeSeries polling.

## Run with the BaSyx stack

From the repository root:

```bash
python3 setup_local_ip.py
docker compose up -d
docker compose up -d --build dpp-web-ui
```

Open:

- Custom DPP UI: `https://<server-ip>:3001`
- Existing BaSyx UI: `https://<server-ip>/` or its existing port

The Docker build reads `HOST_ADDRESS` from the root `.env` and compiles the
public API, protected API, and Keycloak URLs into the static frontend. Run
`python3 setup_local_ip.py` and rebuild this service after the host IP changes.

The development realm template includes redirect URIs for port 3001 and the
Vite development server. Keycloak does not overwrite an already-imported realm;
for an existing development realm, add the port 3001 redirect URI/web origin in
the `basyx-web` client or recreate the disposable development realm.

The repository uses a self-signed TLS certificate. Trust or explicitly allow
the generated `certs/server.crt` in the browser before testing API and login
flows. HTTPS is required for reliable Keycloak PKCE authentication.

## Local frontend development

```bash
cd dpp-web-ui
cp .env.example .env.local
npm ci
npm run dev
```

Update the IP addresses in `.env.local`. The frontend never embeds demo
usernames or passwords.

## Data and access behavior

- Public shell: `GET /public/shells/{base64url(AAS_ID)}`
- Public submodels: `GET /public/submodels/{base64url(SUBMODEL_ID)}`
- Protected live data: `GET /submodels/{base64url(TIMESERIES_ID)}`
- Poll interval: 2 seconds by default
- History: newest 60 unique records in browser memory
- Stale: three failed polls or three successful polls with an unchanged record
- Polling stops on logout, unmount, HTTP 401, or HTTP 403

Tokens stay in the Keycloak JavaScript adapter's in-memory state and are sent
only in the `Authorization` header. The browser does not connect to MQTT, and
there is no application backend-for-frontend.

## Validation

Frontend checks:

```bash
npm run typecheck
npm test
npm run build
```

Container checks from the repository root:

```bash
docker build -t schunk-dpp-monitor:test \
  --build-arg VITE_PUBLIC_API_BASE=https://<server-ip>/public \
  --build-arg VITE_SECURED_API_BASE=https://<server-ip> \
  --build-arg VITE_KEYCLOAK_URL=https://<server-ip>/auth \
  dpp-web-ui
docker compose config
```

API smoke tests can be run with the supplied script. Credentials are provided
through environment variables rather than committed in frontend source:

```bash
API_BASE=https://<server-ip> \
BASYX_USER_PASSWORD='<development-password>' \
BASYX_ADMIN_PASSWORD='<development-password>' \
./dpp-web-ui/tests/api-smoke.sh
```

Use `CURL_INSECURE=1` only for the generated development certificate.

For the live acceptance test:

```bash
python3 simulation/start_simulation.py
```

Log in as the admin development user, confirm the KPI values and charts update,
stop the simulator, and confirm the stale warning appears after approximately
six seconds. Logout must remove live values while leaving all static DPP cards
and contents visible.
