import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/http";
import { publicApi } from "../api/publicApi";
import { config } from "../config";
import { loadPublicAsset } from "../data/aasRepository";
import { parseAssetOverview } from "../data/aasParser";
import {
  loadPublicSubmodels,
  type PublicSubmodelResult,
} from "../data/submodelRepository";
import type { AssetAdministrationShell, AssetOverview } from "../types/aas";

export interface PublicDppProject {
  id: string;
  asset: AssetOverview;
  rawAsset: AssetAdministrationShell;
  submodels: PublicSubmodelResult[];
}

export interface PublicDppState {
  loading: boolean;
  asset?: AssetOverview;
  rawAsset?: AssetAdministrationShell;
  assetError?: ApiError | Error;
  submodels: PublicSubmodelResult[];
  projects: PublicDppProject[];
  selectedProjectId?: string;
  lastRefresh?: Date;
}

export function usePublicDpp() {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<PublicDppState>({
    loading: true,
    submodels: [],
    projects: [],
  });

  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, assetError: undefined }));

    void Promise.allSettled([
      publicApi.getShellDescriptors(controller.signal),
      loadPublicSubmodels(controller.signal),
    ]).then(([descriptorResult, submodelsResult]) => {
      if (controller.signal.aborted) return;
      const submodels = submodelsResult.status === "fulfilled"
        ? submodelsResult.value
        : [];
      const shellIds = descriptorResult.status === "fulfilled"
        ? descriptorResult.value.result.map((descriptor) => descriptor.id)
        : [];
      const ids = shellIds.length ? shellIds : [config.aasId];
      void Promise.allSettled(ids.map((id) => loadPublicAsset(id, controller.signal)))
        .then((assetResults) => {
          if (controller.signal.aborted) return;
          const bySubmodelId = new Map(
            submodels.map((item) => [item.definition.id, item]),
          );
          const projects = assetResults.flatMap((result) => {
            if (result.status !== "fulfilled") return [];
            const { raw } = result.value;
            const referencedIds = (raw.submodels ?? []).flatMap((reference) =>
              (reference.keys ?? [])
                .map((key) => key.value)
                .filter((id) => bySubmodelId.has(id)),
            );
            const projectSubmodels = (referencedIds.length
              ? referencedIds
              : submodels.map((item) => item.definition.id)
            ).map((id) => bySubmodelId.get(id)).filter(
              (item): item is PublicSubmodelResult => Boolean(item),
            );
            const overview = parseAssetOverview(
              raw,
              projectSubmodels.flatMap((item) => item.data ? [item.data] : []),
            );
            return [{ id: overview.aasId, asset: overview, rawAsset: raw, submodels: projectSubmodels }];
          });
          const selectedProjectId = projects.some(
            (project) => project.id === state.selectedProjectId,
          )
            ? state.selectedProjectId
            : projects[0]?.id;
          const selected = projects.find((project) => project.id === selectedProjectId);
          setState({
            loading: false,
            projects,
            selectedProjectId,
            asset: selected?.asset,
            rawAsset: selected?.rawAsset,
            submodels: selected?.submodels ?? [],
            assetError: projects.length ? undefined : new Error("No public AAS projects were found."),
            lastRefresh: new Date(),
          });
        });
    });

    return () => controller.abort();
  }, [reloadKey]);

  const retry = useCallback(() => setReloadKey((key) => key + 1), []);
  const selectProject = useCallback((projectId: string) => {
    setState((current) => {
      const selected = current.projects.find((project) => project.id === projectId);
      return selected
        ? {
            ...current,
            selectedProjectId: projectId,
            asset: selected.asset,
            rawAsset: selected.rawAsset,
            submodels: selected.submodels,
            assetError: undefined,
          }
        : current;
    });
  }, []);
  return { ...state, retry, selectProject };
}
