import { publicApi } from "../api/publicApi";
import { config } from "../config";
import { parseAssetOverview } from "./aasParser";

export async function loadPublicAsset(signal?: AbortSignal) {
  const shell = await publicApi.getShell(config.aasId, signal);
  return {
    raw: shell,
    overview: parseAssetOverview(shell),
  };
}
