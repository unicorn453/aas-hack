import { config } from "../config";
import type { AssetAdministrationShell, AssetMedia, Submodel, SubmodelElement } from "../types/aas";

function modelTypeOf(element: SubmodelElement): string {
  if (typeof element.modelType === "string") return element.modelType;
  if (element.modelType && typeof element.modelType === "object") {
    return element.modelType.name ?? "SubmodelElement";
  }
  return "SubmodelElement";
}

function childrenOf(element: SubmodelElement): SubmodelElement[] {
  const values = Array.isArray(element.value) ? element.value : [];
  const nested = values.filter(
    (value): value is SubmodelElement => Boolean(value) && typeof value === "object",
  );
  return [
    ...nested,
    ...(Array.isArray(element.statements) ? element.statements : []),
    ...(Array.isArray(element.annotations) ? element.annotations : []),
  ];
}

function labelOf(element: SubmodelElement, fallback: string): string {
  const displayName = element.displayName?.find((value) => value.text)?.text;
  return displayName ?? element.idShort ?? fallback;
}

function mediaLabel(element: SubmodelElement, kind: AssetMedia["kind"]): string {
  if (element.idShort) return labelOf(element, kind === "image" ? "Product image" : "Document");
  if (typeof element.value === "string") {
    try {
      const filename = decodeURIComponent(new URL(element.value).pathname.split("/").at(-1) ?? "");
      if (filename) return filename.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ");
    } catch {
      // Fall through to a neutral AAS-derived label.
    }
  }
  return kind === "image" ? "Product image" : "AAS document";
}

function mediaRole(element: SubmodelElement, kind: AssetMedia["kind"]): AssetMedia["role"] | undefined {
  if (kind !== "image") return undefined;
  return /logo|brand|manufacturer/i.test(element.idShort ?? "") ? "logo" : "product";
}

function mediaKind(contentType?: string): AssetMedia["kind"] | undefined {
  if (/^image\//i.test(contentType ?? "")) return "image";
  if (/^application\/pdf$/i.test(contentType ?? "")) return "document";
  return undefined;
}

function contentTypeFor(value: unknown, contentType?: string): string | undefined {
  if (contentType) return contentType;
  if (typeof value !== "string") return undefined;
  const extension = value.split("?")[0].split(".").at(-1)?.toLowerCase();
  return extension === "png" ? "image/png"
    : extension === "jpg" || extension === "jpeg" ? "image/jpeg"
      : extension === "webp" ? "image/webp"
        : extension === "svg" ? "image/svg+xml"
          : extension === "pdf" ? "application/pdf"
            : undefined;
}

function asUrl(value: unknown, contentType?: string): string | undefined {
  if (typeof value !== "string" || !value.trim()) return undefined;
  const trimmed = value.trim();
  if (/^(https?:|data:|blob:)/i.test(trimmed)) return trimmed;
  if (contentType && /^[A-Za-z0-9+/=\r\n]+$/.test(trimmed) && trimmed.length > 32) {
    return `data:${contentType};base64,${trimmed.replace(/\s/g, "")}`;
  }
  if (trimmed.startsWith("/")) return `${config.publicApiBase}${trimmed}`;
  return undefined;
}

function collectElementMedia(element: SubmodelElement, path: string, output: AssetMedia[]): void {
  const type = modelTypeOf(element);
  const contentType = contentTypeFor(element.value, typeof element.contentType === "string" ? element.contentType : undefined);
  const kind = mediaKind(contentType);
  if ((type === "File" || type === "Blob") && kind) {
    const url = asUrl(element.value, contentType);
    if (url) {
      output.push({
        url,
        label: mediaLabel(element, kind),
        kind,
        role: mediaRole(element, kind),
        contentType,
        downloadable: type === "File" || /^application\/pdf$/i.test(contentType ?? ""),
      });
    }
  }
  childrenOf(element).forEach((child, index) =>
    collectElementMedia(child, `${path}.${child.idShort ?? index + 1}`, output),
  );
}

export function collectAssetMedia(
  shell: AssetAdministrationShell | undefined,
  submodels: Submodel[],
): AssetMedia[] {
  const output: AssetMedia[] = [];
  const thumbnail = shell?.assetInformation?.defaultThumbnail;
  const thumbnailType = contentTypeFor(thumbnail?.path, thumbnail?.contentType);
  const thumbnailUrl = asUrl(thumbnail?.path, thumbnailType);
  if (thumbnailUrl) {
    output.push({
      url: thumbnailUrl,
      label: "Asset thumbnail",
      kind: "image",
      role: "product",
      contentType: thumbnailType,
    });
  }
  submodels.forEach((submodel) =>
    (submodel.submodelElements ?? []).forEach((element, index) =>
      collectElementMedia(element, submodel.idShort ?? `Submodel ${index + 1}`, output),
    ),
  );
  return output.filter((item, index, all) => all.findIndex((other) => other.url === item.url) === index);
}
