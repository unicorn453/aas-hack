import { useEffect, useState } from "react";
import { securedApi } from "../api/securedApi";
import type { PublicDppProject } from "./usePublicDpp";

const PRIVATE_PATTERNS = ["timeseries", "telemetry", "live"];

function privateReferenceId(project: PublicDppProject): string | undefined {
  return project.rawAsset.submodels
    ?.flatMap((reference) => reference.keys ?? [])
    .map((key) => key.value)
    .find((id) => PRIVATE_PATTERNS.some((pattern) => id.toLowerCase().includes(pattern)));
}

export function useAdminLiveCapabilities(
  projects: PublicDppProject[],
  enabled: boolean,
  getAccessToken: () => Promise<string>,
) {
  const [capabilities, setCapabilities] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!enabled || !projects.length) {
      setCapabilities({});
      return;
    }
    const controller = new AbortController();
    void (async () => {
      try {
        const token = await getAccessToken();
        const results = await Promise.all(projects.map(async (project) => {
          try {
            const shell = await securedApi.getShell(project.id, token, controller.signal);
            const liveId = shell.submodels
              ?.flatMap((reference) => reference.keys ?? [])
              .map((key) => key.value)
              .find((id) => PRIVATE_PATTERNS.some((pattern) => id.toLowerCase().includes(pattern)))
              ?? privateReferenceId(project);
            return liveId ? [project.id, liveId] as const : undefined;
          } catch {
            return undefined;
          }
        }));
        if (!controller.signal.aborted) {
          setCapabilities(Object.fromEntries(results.filter((item): item is readonly [string, string] => Boolean(item))));
        }
      } catch {
        if (!controller.signal.aborted) setCapabilities({});
      }
    })();
    return () => controller.abort();
  }, [enabled, getAccessToken, projects]);

  return capabilities;
}
