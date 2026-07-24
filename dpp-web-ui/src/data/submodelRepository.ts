import { publicApi } from "../api/publicApi";
import { PUBLIC_SUBMODELS } from "../config";
import type { ApiError } from "../api/http";
import type { Submodel } from "../types/aas";

export interface PublicSubmodelResult {
  definition: (typeof PUBLIC_SUBMODELS)[number];
  data?: Submodel;
  error?: ApiError | Error;
}

export async function loadPublicSubmodels(
  signal?: AbortSignal,
): Promise<PublicSubmodelResult[]> {
  const collection = await publicApi.getSubmodels(signal);
  const byId = new Map(collection.result.map((submodel) => [submodel.id, submodel]));
  return PUBLIC_SUBMODELS.map((definition) => {
    const data = byId.get(definition.id);
    return data
      ? { definition, data }
      : { definition, error: new Error("The public facade did not return this submodel.") };
  });
}
