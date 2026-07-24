import { config } from "../config";
import type {
  AasDescriptor,
  AssetAdministrationShell,
  CollectionResponse,
  Submodel,
  SubmodelDescriptor,
} from "../types/aas";
import { encodeIdentifier, requestJson } from "./http";

export const publicApi = {
  getShellDescriptors(signal?: AbortSignal) {
    return requestJson<CollectionResponse<AasDescriptor>>(
      `${config.publicApiBase}/shell-descriptors`,
      { signal },
    );
  },

  getShell(id: string, signal?: AbortSignal) {
    return requestJson<AssetAdministrationShell>(
      `${config.publicApiBase}/shells/${encodeIdentifier(id)}`,
      { signal },
    );
  },

  getShells(signal?: AbortSignal) {
    return requestJson<CollectionResponse<AssetAdministrationShell>>(
      `${config.publicApiBase}/shells`,
      { signal },
    );
  },

  getSubmodelDescriptors(signal?: AbortSignal) {
    return requestJson<CollectionResponse<SubmodelDescriptor>>(
      `${config.publicApiBase}/submodel-descriptors`,
      { signal },
    );
  },

  getSubmodel(id: string, signal?: AbortSignal) {
    return requestJson<Submodel>(
      `${config.publicApiBase}/submodels/${encodeIdentifier(id)}`,
      { signal },
    );
  },

  getSubmodels(signal?: AbortSignal) {
    return requestJson<CollectionResponse<Submodel>>(
      `${config.publicApiBase}/submodels`,
      { signal },
    );
  },
};
