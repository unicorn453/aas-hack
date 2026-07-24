import type { Field, ProductDocument, ProductPassport, PropertyGroup } from "./types";

type LangString = { language?: string; text?: string };
type AasElement = {
  idShort?: string;
  modelType?: string;
  value?: unknown;
  submodelElements?: AasElement[];
  displayName?: LangString[];
  description?: LangString[];
  contentType?: string;
};
type Submodel = AasElement & { id: string };
type Shell = {
  id: string;
  idShort?: string;
  displayName?: LangString[];
  description?: LangString[];
  assetInformation?: {
    assetKind?: string;
    assetType?: string;
    globalAssetId?: string;
    defaultThumbnail?: { path?: string };
  };
  submodels?: Array<{ keys?: Array<{ value?: string }> }>;
};
type Collection<T> = { result: T[] };

const apiBase = (process.env.PUBLIC_API_INTERNAL_URL ?? "http://dpp-public-api:8080").replace(/\/$/, "");

function encodeIdentifier(value: string): string {
  return Buffer.from(value).toString("base64url");
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Public AAS request failed (${response.status})`);
  return response.json() as Promise<T>;
}

function text(values?: LangString[]): string | undefined {
  return values?.find((item) => item.language?.toLowerCase().startsWith("en"))?.text
    ?? values?.find((item) => item.text)?.text;
}

function children(element: AasElement): AasElement[] {
  if (Array.isArray(element.submodelElements)) return element.submodelElements;
  if (Array.isArray(element.value)) {
    return element.value.filter((item): item is AasElement => Boolean(item) && typeof item === "object");
  }
  return [];
}

function primitive(value: unknown): string | undefined {
  if (value === undefined || value === null || value === "") return undefined;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    const item = value.find((entry) => typeof entry === "object" && entry && "text" in entry) as LangString | undefined;
    return item?.text;
  }
  return undefined;
}

function label(element: AasElement): string {
  return text(element.displayName) ?? humanize(element.idShort ?? "AAS element");
}

function humanize(value: string): string {
  return value.replace(/__\d+__$/g, "").replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function leafFields(elements: AasElement[], output: Field[] = []): Field[] {
  for (const element of elements) {
    const nested = children(element);
    if (nested.length) leafFields(nested, output);
    else {
      const value = primitive(element.value);
      if (value) output.push({ label: label(element), value });
    }
  }
  return output;
}

function findSubmodel(submodels: Submodel[], needle: string): Submodel | undefined {
  return submodels.find((item) => (item.idShort ?? "").toLowerCase().includes(needle.toLowerCase()));
}

function findValue(elements: AasElement[], needle: string): string | undefined {
  for (const element of elements) {
    if ((element.idShort ?? "").toLowerCase().includes(needle.toLowerCase())) {
      const value = primitive(element.value);
      if (value) return value;
    }
    const nested = findValue(children(element), needle);
    if (nested) return nested;
  }
  return undefined;
}

function description(shell: Shell): string | undefined {
  return text(shell.description);
}

export async function getAvailableProducts(): Promise<Array<{ id: string; name: string }>> {
  const descriptors = await getJson<Collection<Shell>>("/public/shell-descriptors");
  return descriptors.result.map((shell) => ({
    id: shell.id,
    name: text(shell.displayName) ?? shell.idShort ?? shell.id,
  }));
}

export async function getSelectedProduct(aasId?: string): Promise<ProductPassport> {
  const selectedId = aasId ?? (await getAvailableProducts())[0]?.id;
  if (!selectedId) throw new Error("No public AAS asset is available");
  const shell = await getJson<Shell>(`/public/shells/${encodeIdentifier(selectedId)}`);
  const collection = await getJson<Collection<Submodel>>("/public/submodels");
  const referenced = new Set((shell.submodels ?? []).flatMap((ref) => (ref.keys ?? []).map((key) => key.value).filter(Boolean) as string[]));
  const submodels = collection.result.filter((item) => referenced.size === 0 || referenced.has(item.id));
  const nameplate = findSubmodel(submodels, "nameplate");
  const technical = findSubmodel(submodels, "technical");
  const handover = findSubmodel(submodels, "handover");
  const name = findValue(nameplate ? children(nameplate) : [], "designation") ?? text(shell.displayName) ?? shell.idShort ?? shell.id;
  const manufacturer = findValue(nameplate ? children(nameplate) : [], "manufacturername");
  const nameplateFields = leafFields(nameplate ? children(nameplate) : []);
  const technicalFields = leafFields(technical ? children(technical) : []);
  const documents = leafFields(handover ? children(handover) : [])
    .filter((field) => /^https?:\/\//.test(field.value))
    .map((field, index) => ({ id: `${field.value}-${index}`, title: field.label, type: "AAS document", action: field.value.toLowerCase().endsWith(".pdf") ? "open" as const : "download" as const, href: field.value }));

  const technicalGroup: PropertyGroup | undefined = technicalFields.length
    ? { title: technical?.idShort ? humanize(technical.idShort) : "Technical data", properties: technicalFields }
    : undefined;
  return {
    aasId: shell.id,
    name,
    manufacturer,
    productType: shell.assetInformation?.assetType,
    description: description(shell),
    imageUrl: shell.assetInformation?.defaultThumbnail?.path ?? "/product.svg",
    imageAlt: name,
    highlights: nameplateFields.slice(0, 4),
    nameplate: nameplateFields,
    technicalData: technicalGroup ? [technicalGroup] : [],
    documents,
  };
}
