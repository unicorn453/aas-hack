import Keycloak, { type KeycloakInitOptions } from "keycloak-js";
import { config } from "../config";

export const keycloak = new Keycloak({
  url: config.keycloakUrl,
  realm: config.keycloakRealm,
  clientId: config.keycloakClientId,
});

let initialization: Promise<boolean> | undefined;

export function initializeKeycloak(): Promise<boolean> {
  if (!initialization) {
    const options: KeycloakInitOptions = {
      onLoad: "check-sso",
      silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      pkceMethod: "S256",
      checkLoginIframe: false,
      flow: "standard",
      responseMode: "query",
    };
    initialization = keycloak.init(options);
  }
  return initialization;
}

export async function currentAccessToken(): Promise<string> {
  if (!keycloak.authenticated) {
    throw new Error("No authenticated Keycloak session.");
  }
  await keycloak.updateToken(30);
  if (!keycloak.token) {
    throw new Error("Keycloak did not provide an access token.");
  }
  return keycloak.token;
}
