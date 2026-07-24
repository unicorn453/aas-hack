import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createIndustrialTheme } from "../theme";

const state = vi.hoisted(() => ({
  auth: {
    status: "anonymous",
    authenticated: false,
    isAdmin: false,
    user: undefined as
      | { username: string; displayName: string; roles: string[] }
      | undefined,
    error: undefined as string | undefined,
    login: vi.fn(),
    logout: vi.fn(),
    getAccessToken: vi.fn(),
  },
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => state.auth,
}));

vi.mock("../hooks/useLiveTelemetry", () => ({
  useLiveTelemetry: () => ({
    connection: "idle",
    records: [],
    consecutiveFailures: 0,
  }),
}));

import { TelemetryGate } from "./TelemetryGate";

function renderGate() {
  return render(
    <ThemeProvider theme={createIndustrialTheme("dark")}>
      <TelemetryGate />
    </ThemeProvider>,
  );
}

describe("telemetry authorization gate", () => {
  beforeEach(() => {
    state.auth.status = "anonymous";
    state.auth.authenticated = false;
    state.auth.isAdmin = false;
    state.auth.user = undefined;
  });

  it("keeps live telemetry locked for anonymous visitors", () => {
    renderGate();
    expect(
      screen.getByText("Administrator login required"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Live machine signal")).not.toBeInTheDocument();
  });

  it("shows a clear permission-denied state to basyx-user", () => {
    state.auth.status = "authenticated";
    state.auth.authenticated = true;
    state.auth.user = {
      username: "basyx-user",
      displayName: "BaSyx User",
      roles: ["user"],
    };
    renderGate();
    expect(
      screen.getByText("Administrator permission required"),
    ).toBeInTheDocument();
    expect(screen.getByText(/basyx-user/)).toBeInTheDocument();
  });

  it("opens the live dashboard only for the admin role", () => {
    state.auth.status = "authenticated";
    state.auth.authenticated = true;
    state.auth.isAdmin = true;
    state.auth.user = {
      username: "basyx-admin",
      displayName: "BaSyx Admin",
      roles: ["admin", "user"],
    };
    renderGate();
    expect(screen.getByText("Live machine signal")).toBeInTheDocument();
  });
});
