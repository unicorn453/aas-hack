import { describe, expect, it, vi } from "vitest";
import { ApiError, encodeIdentifier, requestJson } from "./http";

describe("encodeIdentifier", () => {
  it("uses unpadded base64url encoding required by BaSyx", () => {
    const encoded = encodeIdentifier(
      "https://example.org/aas/schunk/pgn-plus-p-64-1",
    );
    expect(encoded).not.toMatch(/[+/=]/);
    expect(encoded).toBe(
      "aHR0cHM6Ly9leGFtcGxlLm9yZy9hYXMvc2NodW5rL3Bnbi1wbHVzLXAtNjQtMQ",
    );
  });

  it.each([
    [401, "unauthorized"],
    [403, "forbidden"],
    [404, "not-found"],
    [502, "bad-gateway"],
  ] as const)("classifies HTTP %i responses", async (status, kind) => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("{}", { status }),
    );
    await expect(requestJson("/test")).rejects.toMatchObject({
      status,
      kind,
    } satisfies Partial<ApiError>);
  });
});
