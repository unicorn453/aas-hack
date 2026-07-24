import { publicApi } from "../api/publicApi";
import { PUBLIC_SUBMODELS } from "../config";
import type { ApiError } from "../api/http";
import type { Submodel } from "../types/aas";

export interface PublicSubmodelDefinition {
  id: string;
  title: string;
  description: string;
  template: string;
  icon: string;
}

export interface PublicSubmodelResult {
  definition: PublicSubmodelDefinition;
  data?: Submodel;
  error?: ApiError | Error;
}

function titleFor(submodel: Submodel): string {
  const value = submodel.idShort ?? "Submodel";
  return value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function definitionFor(submodel: Submodel): PublicSubmodelDefinition {
  const title = titleFor(submodel);
  const lower = title.toLowerCase();
  const known = PUBLIC_SUBMODELS.find((item) => item.id === submodel.id);
  if (known) return known;
  const icon = lower.includes("nameplate")
    ? "badge"
    : lower.includes("technical")
      ? "settings"
      : lower.includes("maintenance")
        ? "build"
        : lower.includes("carbon")
          ? "eco"
          : "description";
  return {
    id: submodel.id,
    title,
    description: "Structured product passport information exposed by this asset.",
    template: submodel.semanticId?.keys?.[0]?.value ?? "AAS submodel",
    icon,
  };
}

export async function loadPublicSubmodels(
  signal?: AbortSignal,
): Promise<PublicSubmodelResult[]> {
  const collection = await publicApi.getSubmodels(signal);
  return collection.result.map((data) => ({
    definition: definitionFor(data),
    data,
  }));
}
