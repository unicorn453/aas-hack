import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/http";
import { securedApi } from "../api/securedApi";
import { config } from "../config";
import { parseIdtaTimeSeries } from "../data/timeSeriesParser";
import type { TimeSeriesRecord } from "../types/aas";

export type LiveConnectionState =
  | "idle"
  | "connecting"
  | "connected"
  | "stale"
  | "permission-denied"
  | "authentication-failed"
  | "not-found"
  | "unavailable";

export interface LiveTelemetryState {
  connection: LiveConnectionState;
  records: TimeSeriesRecord[];
  lastSuccessAt?: Date;
  segmentLastUpdate?: string;
  consecutiveFailures: number;
  error?: string;
}

const initialState: LiveTelemetryState = {
  connection: "idle",
  records: [],
  consecutiveFailures: 0,
};

interface UseLiveTelemetryOptions {
  enabled: boolean;
  getAccessToken: () => Promise<string>;
}

export function useLiveTelemetry({
  enabled,
  getAccessToken,
}: UseLiveTelemetryOptions): LiveTelemetryState {
  const [state, setState] = useState<LiveTelemetryState>(initialState);
  const latestSignature = useRef<string | undefined>(undefined);
  const unchangedPolls = useRef(0);

  useEffect(() => {
    if (!enabled) {
      latestSignature.current = undefined;
      unchangedPolls.current = 0;
      setState(initialState);
      return;
    }

    let stopped = false;
    let timer: number | undefined;
    let activeController: AbortController | undefined;
    setState({ ...initialState, connection: "connecting" });

    const schedule = () => {
      if (!stopped) timer = window.setTimeout(poll, config.pollIntervalMs);
    };

    const poll = async () => {
      activeController = new AbortController();
      try {
        const token = await getAccessToken();
        if (stopped) return;
        const submodel = await securedApi.getTimeSeries(
          token,
          activeController.signal,
        );
        const parsed = parseIdtaTimeSeries(submodel);
        if (stopped) return;

        const newest = parsed.records.at(-1);
        if (newest?.signature === latestSignature.current) {
          unchangedPolls.current += 1;
        } else {
          unchangedPolls.current = 0;
          latestSignature.current = newest?.signature;
        }

        setState((current) => {
          const merged = [...current.records];
          for (const record of parsed.records) {
            if (!merged.some((item) => item.signature === record.signature)) {
              merged.push(record);
            }
          }
          return {
            connection: unchangedPolls.current >= 3 ? "stale" : "connected",
            records: merged.slice(-60),
            lastSuccessAt: new Date(),
            segmentLastUpdate: parsed.lastUpdate,
            consecutiveFailures: 0,
            error:
              unchangedPolls.current >= 3
                ? "The API is reachable, but the telemetry record has not changed for three polling cycles."
                : undefined,
          };
        });
        schedule();
      } catch (error) {
        if (
          stopped ||
          (error instanceof DOMException && error.name === "AbortError")
        ) {
          return;
        }

        if (error instanceof ApiError && error.kind === "forbidden") {
          setState((current) => ({
            ...current,
            connection: "permission-denied",
            error:
              "The backend denied access to live telemetry. Administrator permission is required.",
          }));
          stopped = true;
          return;
        }
        if (error instanceof ApiError && error.kind === "unauthorized") {
          setState((current) => ({
            ...current,
            connection: "authentication-failed",
            error:
              "Your session is no longer authorized. Sign in again to resume live telemetry.",
          }));
          stopped = true;
          return;
        }
        if (error instanceof ApiError && error.kind === "not-found") {
          setState((current) => ({
            ...current,
            connection: "not-found",
            error:
              "The configured TimeSeries submodel was not found on the protected API.",
          }));
          stopped = true;
          return;
        }

        setState((current) => {
          const failures = current.consecutiveFailures + 1;
          return {
            ...current,
            connection: failures >= 3 ? "stale" : "unavailable",
            consecutiveFailures: failures,
            error:
              error instanceof Error
                ? error.message
                : "The live telemetry API is unavailable.",
          };
        });
        schedule();
      }
    };

    void poll();
    return () => {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
      activeController?.abort();
    };
  }, [enabled, getAccessToken]);

  return state;
}
