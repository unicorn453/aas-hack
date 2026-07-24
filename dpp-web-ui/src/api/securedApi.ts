import { config } from "../config";
import type { AssetAdministrationShell, Submodel } from "../types/aas";
import { encodeIdentifier, requestJson } from "./http";

function bearerHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export const securedApi = {
  async uploadAasx(file: File, token: string): Promise<unknown> {
    const body = new FormData();
    body.append("file", file, file.name);
    const response = await fetch(`${config.securedApiBase}/upload`, {
      method: "POST",
      headers: bearerHeaders(token),
      body,
    });
    if (!response.ok) {
      const message = response.status === 403
        ? "Your account is not allowed to upload AASX files."
        : `AASX upload failed with HTTP ${response.status}.`;
      throw new Error(message);
    }
    const contentType = response.headers.get("content-type") ?? "";
    return contentType.includes("json") ? response.json() : response.text();
  },

  getShell(id: string, token: string, signal?: AbortSignal) {
    return requestJson<AssetAdministrationShell>(
      `${config.securedApiBase}/shells/${encodeIdentifier(id)}`,
      { headers: bearerHeaders(token), signal },
    );
  },

  getSubmodel(id: string, token: string, signal?: AbortSignal) {
    return requestJson<Submodel>(
      `${config.securedApiBase}/submodels/${encodeIdentifier(id)}`,
      { headers: bearerHeaders(token), signal },
    );
  },

  getTimeSeries(token: string, signal?: AbortSignal) {
    return this.getSubmodel(config.timeSeriesId, token, signal);
  },
};
