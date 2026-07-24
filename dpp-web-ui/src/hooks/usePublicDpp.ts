import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api/http";
import { loadPublicAsset } from "../data/aasRepository";
import {
  loadPublicSubmodels,
  type PublicSubmodelResult,
} from "../data/submodelRepository";
import type { AssetAdministrationShell, AssetOverview } from "../types/aas";

export interface PublicDppState {
  loading: boolean;
  asset?: AssetOverview;
  rawAsset?: AssetAdministrationShell;
  assetError?: ApiError | Error;
  submodels: PublicSubmodelResult[];
  lastRefresh?: Date;
}

export function usePublicDpp() {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<PublicDppState>({
    loading: true,
    submodels: [],
  });

  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, assetError: undefined }));

    void Promise.allSettled([
      loadPublicAsset(controller.signal),
      loadPublicSubmodels(controller.signal),
    ]).then(([assetResult, submodelsResult]) => {
      if (controller.signal.aborted) return;
      const next: PublicDppState = {
        loading: false,
        submodels:
          submodelsResult.status === "fulfilled"
            ? submodelsResult.value
            : [],
        lastRefresh: new Date(),
      };
      if (assetResult.status === "fulfilled") {
        next.asset = assetResult.value.overview;
        next.rawAsset = assetResult.value.raw;
      } else {
        next.assetError =
          assetResult.reason instanceof Error
            ? assetResult.reason
            : new Error("The public asset could not be loaded.");
      }
      setState(next);
    });

    return () => controller.abort();
  }, [reloadKey]);

  const retry = useCallback(() => setReloadKey((key) => key + 1), []);
  return { ...state, retry };
}
