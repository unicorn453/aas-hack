export const AAS_ID =
  import.meta.env.VITE_AAS_ID ??
  "https://example.org/aas/schunk/pgn-plus-p-64-1";

export const TIMESERIES_ID =
  import.meta.env.VITE_TIMESERIES_ID ??
  "https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries";

export const PUBLIC_SUBMODELS = [
  {
    id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/nameplate",
    title: "Nameplate",
    description: "Manufacturer identity, product designation, serial information and origin.",
    template: "IDTA Digital Nameplate",
    icon: "badge",
  },
  {
    id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/technicaldata",
    title: "Technical Data",
    description: "Core mechanical, electrical and operating characteristics of the gripper.",
    template: "IDTA Technical Data",
    icon: "settings",
  },
  {
    id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/carbonfootprint",
    title: "Carbon Footprint",
    description: "Lifecycle carbon information and product-footprint declarations.",
    template: "IDTA Carbon Footprint",
    icon: "eco",
  },
  {
    id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/maintenanceinstructions",
    title: "Maintenance Instructions",
    description: "Maintenance intervals, required activities and service guidance.",
    template: "IDTA Maintenance Instructions",
    icon: "build",
  },
  {
    id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/handoverdocumentation",
    title: "Handover Documentation",
    description: "Technical documents, manuals and handover records for operation.",
    template: "IDTA Handover Documentation",
    icon: "description",
  },
] as const;

const currentOrigin =
  typeof window === "undefined" ? "http://localhost:3001" : window.location.origin;

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function positiveNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const config = {
  publicApiBase: trimTrailingSlash(
    import.meta.env.VITE_PUBLIC_API_BASE ?? `${currentOrigin}/public`,
  ),
  securedApiBase: trimTrailingSlash(
    import.meta.env.VITE_SECURED_API_BASE ?? currentOrigin,
  ),
  keycloakUrl: trimTrailingSlash(
    import.meta.env.VITE_KEYCLOAK_URL ?? `${currentOrigin}/auth`,
  ),
  keycloakRealm: import.meta.env.VITE_KEYCLOAK_REALM ?? "basyx",
  keycloakClientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "basyx-web",
  aasId: AAS_ID,
  timeSeriesId: TIMESERIES_ID,
  pollIntervalMs: positiveNumber(import.meta.env.VITE_POLL_INTERVAL_MS, 2_000),
  requestTimeoutMs: positiveNumber(
    import.meta.env.VITE_REQUEST_TIMEOUT_MS,
    8_000,
  ),
} as const;
