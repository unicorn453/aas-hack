# Custom DPP and Live Telemetry Web UI — Implementation Plan

## Mission

Build a separate, polished industrial web application for the Schunk PGN gripper. It must make static Digital Product Passport data publicly readable while protecting live telemetry with Keycloak authentication and an administrator role.

The application belongs in:

```text
dpp-web-ui/
```

It must run as a separate Docker service beside the existing BaSyx stack. Do not replace or modify the existing BaSyx Web UI.

## Required user experience

### Anonymous visitor

An unauthenticated visitor must be able to:

1. Open the website.
2. See the Schunk gripper asset overview immediately.
3. See the five static DPP submodels:
   - Nameplate
   - Technical Data
   - Carbon Footprint
   - Maintenance Instructions
   - Handover Documentation
4. Open and read the structured contents of those submodels.
5. See a clear locked Live Telemetry section explaining that administrator login is required.

The visitor must never be redirected to Keycloak merely to view static DPP information.

### Authenticated normal user

After Keycloak login as `basyx-user`:

- Static DPP data remains available.
- Live telemetry remains hidden or locked.
- The UI must show a clear “Administrator permission required” message.
- A backend `403` response must be handled correctly even if the browser token appears valid.

### Authenticated administrator

After Keycloak login as `basyx-admin`:

- Static DPP data remains available.
- Live telemetry becomes available.
- KPI values update approximately every two seconds.
- Charts show recent telemetry history.
- The interface displays connection state, latest sample time, and stale-data warnings.

## Technology requirements

Use:

- React
- TypeScript
- Vite
- React Router if multiple views are used
- A mature component system such as MUI, Mantine, or an equivalent polished system
- Recharts, ECharts, or an equivalent charting library
- Keycloak Authorization Code + PKCE
- A production Dockerfile using a Node build stage and nginx static serving

Do not add a backend-for-frontend in version one. The browser may call the public and protected HTTPS APIs directly after Keycloak login. Keep access tokens in memory where practical and never put tokens in URLs.

Do not connect browsers directly to MQTT. MQTT continues to feed the protected BaSyx TimeSeries through the existing subscriber.

## Visual and interaction design

The website should look like a modern industrial monitoring product, not a raw JSON viewer.

### Visual language

- Clean industrial dashboard aesthetic.
- Dark navy/charcoal base with cyan/blue telemetry accents and restrained orange warning accents.
- High contrast for machine-room or laboratory displays.
- Rounded cards with subtle borders and restrained shadows.
- Consistent spacing and typography.
- Do not use excessive gradients, oversized marketing illustrations, or decorative animation that distracts from data.
- Use clear semantic colors:
  - Green: healthy/connected/running.
  - Blue: informational/normal.
  - Amber: warning/stale/attention.
  - Red: error/disconnected/permission denied.
  - Gray: unavailable/not configured.

### Main dashboard layout

Use a responsive layout with the following hierarchy:

1. **Top navigation bar**
   - Product name: `Schunk PGN+ P 64-1`
   - Small `Digital Product Passport` label.
   - API connection badge.
   - Last successful refresh time.
   - Login/logout control.
   - Theme toggle.

2. **Asset hero card**
   - Asset name and type.
   - Global asset ID.
   - AAS ID in a secondary details area.
   - Thumbnail when available.
   - A compact “Public DPP” badge.

3. **DPP submodel grid**
   - Five cards, each with icon, title, short description, semantic/template label, and availability state.
   - Clicking a card opens a readable structured detail drawer or detail page.
   - Prefer labels and grouped sections over exposing raw JSON by default.
   - Include a “View raw JSON” secondary action for technical users.

4. **Live telemetry panel**
   - Full-width section visually separated from static DPP information.
   - When logged out: locked panel with explanation and login button.
   - When logged in as non-admin: permission-denied panel.
   - When logged in as admin: live cards, charts, and status timeline.

5. **Footer/status area**
   - Endpoint mode.
   - Current authenticated user, if any.
   - API status.
   - Data freshness.

### Live KPI cards

Show these values prominently:

- Jaw Position
- Grip Force
- Temperature
- Motor Current
- Cycle Count
- Current State

Each card should include:

- Current value.
- Unit where applicable.
- Small trend indicator compared with the previous sample.
- Timestamp/freshness label.
- Warning styling when stale or outside sensible demo limits.

### Charts

Provide:

- Jaw Position over time.
- Grip Force over time.
- Temperature over time.
- Motor Current over time.

Use a bounded in-memory history of the latest 60 records. Make chart tooltips readable and include timestamp, value, and unit. Use accessible labels and a non-color-only distinction for important states.

## Existing API contract

The public facade is read-only and anonymous:

```text
GET /public/shell-descriptors
GET /public/shells
GET /public/shells/{base64url(AAS_ID)}
GET /public/submodel-descriptors
GET /public/submodels
GET /public/submodels/{base64url(SUBMODEL_ID)}
```

The protected BaSyx API requires a Keycloak bearer token:

```text
GET /shells/{base64url(AAS_ID)}
GET /submodels/{base64url(TIMESERIES_ID)}
```

Keycloak configuration:

```text
Issuer:    https://<server-ip>/auth/realms/basyx
Realm:     basyx
Client:    basyx-web
Flow:      Authorization Code + PKCE
```

Frontend environment variables:

```env
VITE_PUBLIC_API_BASE=https://<server-ip>/public
VITE_SECURED_API_BASE=https://<server-ip>
VITE_KEYCLOAK_URL=https://<server-ip>/auth
VITE_KEYCLOAK_REALM=basyx
VITE_KEYCLOAK_CLIENT_ID=basyx-web
VITE_AAS_ID=https://example.org/aas/schunk/pgn-plus-p-64-1
VITE_TIMESERIES_ID=https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries
VITE_POLL_INTERVAL_MS=2000
```

The AAS ID is:

```text
https://example.org/aas/schunk/pgn-plus-p-64-1
```

The five public submodel IDs are:

```text
https://example.org/submodels/schunk/pgn-plus-p-64-1/carbonfootprint
https://example.org/submodels/schunk/pgn-plus-p-64-1/technicaldata
https://example.org/submodels/schunk/pgn-plus-p-64-1/nameplate
https://example.org/submodels/schunk/pgn-plus-p-64-1/maintenanceinstructions
https://example.org/submodels/schunk/pgn-plus-p-64-1/handoverdocumentation
```

The protected live submodel ID is:

```text
https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries
```

## Data handling

Create typed models and adapters for:

- AAS descriptor.
- Asset Administration Shell.
- Submodel descriptor.
- Submodel and nested submodel elements.
- IDTA TimeSeries internal segment.
- TimeSeries record.
- Authentication state.

The TimeSeries data is located under:

```text
Submodel
└── Segments
    └── InternalSegment
        └── Records
            └── Record
```

Expected record fields:

```text
Time
JawPosition
GripForce
Temperature
MotorCurrent
CycleCount
CurrentState
```

Polling rules:

1. Do not call the protected TimeSeries endpoint before login.
2. Require the `admin` role before enabling polling.
3. Poll every two seconds by default.
4. Cancel polling on logout or component unmount.
5. Keep at most 60 records in memory.
6. Mark data stale after three consecutive failed polls.
7. Preserve the last valid chart history during short outages.
8. Stop polling and show permission denied on `403`.

## Suggested frontend structure

```text
dpp-web-ui/
├── src/
│   ├── api/
│   │   ├── publicApi.ts
│   │   └── securedApi.ts
│   ├── auth/
│   │   ├── keycloak.ts
│   │   └── AuthContext.tsx
│   ├── data/
│   │   ├── aasRepository.ts
│   │   ├── submodelRepository.ts
│   │   └── timeSeriesParser.ts
│   ├── components/
│   │   ├── AppShell.tsx
│   │   ├── AssetOverview.tsx
│   │   ├── StaticSubmodelGrid.tsx
│   │   ├── SubmodelViewer.tsx
│   │   ├── LiveTelemetryDashboard.tsx
│   │   ├── AuthGate.tsx
│   │   ├── StatusBadge.tsx
│   │   └── charts/
│   ├── pages/
│   │   └── DashboardPage.tsx
│   ├── types/
│   └── main.tsx
├── public/
├── Dockerfile
├── nginx.conf
├── package.json
├── tsconfig.json
├── vite.config.ts
├── .env.example
└── README.md
```

## Docker integration

Add a separate service to the compose stack:

```yaml
dpp-web-ui:
  build: ./dpp-web-ui
  container_name: dpp-web-ui
  ports:
    - "3001:80"
  restart: unless-stopped
```

The existing BaSyx Web UI must remain available. The custom site must be reachable at:

```text
http://<server-ip>:3001
```

Optionally add an nginx route later:

```text
https://<server-ip>/custom-ui/
```

No MQTT browser client is required.

## Error and loading states

Implement deliberate states for:

- Initial loading skeleton.
- Public API unavailable.
- Asset not found.
- Static submodel unavailable.
- Login required.
- Authenticated but not administrator.
- Live data loading.
- Live data stale.
- Live API disconnected.
- Logout transition.

Never show a blank panel when an API request fails. Every failure must identify whether the issue is public data, authentication, permissions, or connectivity.

## Test and acceptance criteria

The implementer must verify:

```text
Anonymous public shell descriptors → 200
Anonymous public shell → 200
Anonymous public submodels → 200
Anonymous protected TimeSeries → 401
basyx-user protected TimeSeries → 403
basyx-admin protected TimeSeries → 200
```

Manual UI test:

1. Open the custom UI while logged out.
2. Confirm asset overview and five static submodels are visible.
3. Open static submodel contents without login.
4. Confirm Live Telemetry is locked.
5. Log in as `basyx-user` and confirm telemetry remains locked.
6. Log in as `basyx-admin` and confirm telemetry appears.
7. Start the MQTT simulator.
8. Confirm values and charts update every two seconds.
9. Stop the simulator and confirm stale-data handling.
10. Log out and confirm live values disappear while static content remains.

## Non-goals for version one

- No AAS editing.
- No delete or upload actions.
- No direct MQTT browser connection.
- No public live telemetry.
- No multi-asset management UI.
- No separate backend-for-frontend.
