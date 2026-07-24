import type {
  AssetAdministrationShell,
  AssetOverview,
  LangString,
} from "../types/aas";

function preferredText(values: LangString[] | undefined): string | undefined {
  if (!Array.isArray(values)) return undefined;
  return (
    values.find((entry) => entry.language?.toLowerCase().startsWith("en"))
      ?.text ?? values.find((entry) => entry.text)?.text
  );
}

export function parseAssetOverview(
  shell: AssetAdministrationShell,
): AssetOverview {
  const info = shell.assetInformation;
  const specificIds = info?.specificAssetIds ?? [];
  const manufacturerId = specificIds.find((entry) =>
    entry.name?.toLowerCase().includes("manufacturer"),
  )?.value;

  return {
    name: preferredText(shell.displayName) ??
      (shell.idShort && shell.idShort.toLowerCase() !== "dpp"
        ? shell.idShort
        : "Schunk PGN+ P 64-1"),
    manufacturer: manufacturerId ?? "SCHUNK",
    productFamily: "PGN-plus-P",
    assetKind: info?.assetKind ?? "Instance",
    assetType: info?.assetType ?? "Parallel gripper",
    globalAssetId: info?.globalAssetId ?? "Not provided by the AAS",
    aasId: shell.id,
    thumbnail: info?.defaultThumbnail?.path,
  };
}

export function referenceValue(
  reference: { keys?: Array<{ value: string }> } | undefined,
): string | undefined {
  return reference?.keys?.map((key) => key.value).filter(Boolean).join(" → ");
}

export function displayText(values: LangString[] | undefined): string | undefined {
  return preferredText(values);
}
