import { config } from "../config";

export type ApiErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not-found"
  | "bad-gateway"
  | "timeout"
  | "network"
  | "http"
  | "invalid-response";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: ApiErrorKind,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function kindForStatus(status: number): ApiErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not-found";
  if (status === 502) return "bad-gateway";
  return "http";
}

function messageForStatus(status: number): string {
  if (status === 401) return "Authentication is required or the session has expired.";
  if (status === 403) return "The API denied permission for this resource.";
  if (status === 404) return "The requested API resource was not found.";
  if (status === 502) return "The gateway could not reach the upstream AAS service.";
  return `Request failed with HTTP ${status}.`;
}

export async function requestJson<T>(
  url: string,
  init: RequestInit = {},
  timeoutMs = config.requestTimeoutMs,
): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort("timeout"), timeoutMs);
  const outerSignal = init.signal;

  const abortFromOuter = () => controller.abort(outerSignal?.reason);
  outerSignal?.addEventListener("abort", abortFromOuter, { once: true });

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });

    if (!response.ok) {
      throw new ApiError(
        messageForStatus(response.status),
        kindForStatus(response.status),
        response.status,
      );
    }

    try {
      return (await response.json()) as T;
    } catch {
      throw new ApiError(
        "The API returned an invalid JSON response.",
        "invalid-response",
        response.status,
      );
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted) {
      if (outerSignal?.aborted) {
        throw new DOMException("Request cancelled.", "AbortError");
      }
      throw new ApiError(
        `The API did not respond within ${Math.round(timeoutMs / 1000)} seconds.`,
        "timeout",
      );
    }
    throw new ApiError(
      error instanceof Error
        ? `Unable to reach the API: ${error.message}`
        : "Unable to reach the API.",
      "network",
    );
  } finally {
    window.clearTimeout(timeout);
    outerSignal?.removeEventListener("abort", abortFromOuter);
  }
}

export function encodeIdentifier(identifier: string): string {
  const bytes = new TextEncoder().encode(identifier);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
