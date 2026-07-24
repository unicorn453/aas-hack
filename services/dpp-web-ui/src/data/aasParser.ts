import type {
  AssetAdministrationShell,
  AssetOverview,
  LangString,
} from "../types/aas";
import type { Submodel } from "../types/aas";
import type { SubmodelElement } from "../types/aas";

function preferredText(values: LangString[] | undefined): string | undefined {
  if (!Array.isArray(values)) return undefined;
  return (
    values.find((entry) => entry.language?.toLowerCase().startsWith("en"))
      ?.text ?? values.find((entry) => entry.text)?.text
  );
}

export function parseAssetOverview(
  shell: AssetAdministrationShell,
  submodels: Submodel[] = [],
): AssetOverview {
  const info = shell.assetInformation;
  const specificIds = info?.specificAssetIds ?? [];
  const manufacturerId = specificIds.find((entry) =>
    entry.name?.toLowerCase().includes("manufacturer"),
  )?.value;
  const nameplate = submodels.find((submodel) =>
    /nameplate/i.test(submodel.idShort ?? ""),
  );
  const propertyValue = (pattern: RegExp): string | undefined => {
    const stack = [...(nameplate?.submodelElements ?? [])];
    while (stack.length) {
      const element = stack.shift();
      if (!element) continue;
      if (pattern.test(element.idShort ?? "")) {
        if (typeof element.value === "string") return element.value;
        if (Array.isArray(element.value)) {
          const languageValues = element.value.filter(
            (item): item is { text: string; language?: string } =>
              Boolean(item) && typeof item === "object" && typeof (item as { text?: unknown }).text === "string",
          );
          return languageValues.find((item) => item.language?.toLowerCase().startsWith("en"))?.text
            ?? languageValues[0]?.text;
        }
      }
      if (Array.isArray(element.value)) {
        stack.push(...element.value.filter((item): item is SubmodelElement => Boolean(item) && typeof item === "object"));
      }
    }
    return undefined;
  };
  const manufacturer = manufacturerId ?? propertyValue(/^manufacturer(name|companyname)$/i);
  const productFamily = propertyValue(/^manufacturerproductfamily$/i);
  const productDesignation = propertyValue(/^manufacturer(productdesignation|producttype)$/i);

  return {
    name: preferredText(shell.displayName) ?? productDesignation ??
      (shell.idShort && shell.idShort.toLowerCase() !== "dpp"
        ? shell.idShort
        : shell.id.split("/").at(-1) ?? "Unnamed asset"),
    manufacturer: manufacturer ?? "Not provided",
    productFamily: productFamily ?? info?.assetType ?? "Not provided",
    assetKind: info?.assetKind ?? "Not provided",
    assetType: info?.assetType ?? "Not provided",
    globalAssetId: info?.globalAssetId ?? "Not provided",
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
