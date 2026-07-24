import { publicApi } from "../api/publicApi";
import { config } from "../config";
import { parseAssetOverview } from "./aasParser";

export async function loadPublicAsset(
  aasId = config.aasId,
  signal?: AbortSignal,
) {
  const shell = await publicApi.getShell(aasId, signal);
  return {
    raw: shell,
    overview: parseAssetOverview(shell),
  };
}
