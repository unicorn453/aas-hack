import { displayText, referenceValue } from "./aasParser";
import type {
  LangString,
  StructuredElement,
  Submodel,
  SubmodelElement,
} from "../types/aas";

function modelTypeOf(element: SubmodelElement): string {
  if (typeof element.modelType === "string") return element.modelType;
  if (
    element.modelType &&
    typeof element.modelType === "object" &&
    typeof element.modelType.name === "string"
  ) {
    return element.modelType.name;
  }
  return "SubmodelElement";
}

export function humanizeIdShort(value: string): string {
  return value
    .replace(/__\d+__$/g, "")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function languageValue(value: unknown): string | undefined {
  if (!Array.isArray(value)) return undefined;
  const values = value as LangString[];
  const english = values.find((entry) =>
    entry.language?.toLowerCase().startsWith("en"),
  );
  return english?.text ?? values.find((entry) => entry.text)?.text;
}

function primitiveValue(value: unknown): string | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return undefined;
}

function childElements(element: SubmodelElement): SubmodelElement[] {
  if (Array.isArray(element.value)) {
    const elementValues = element.value.filter(
      (item): item is SubmodelElement =>
        Boolean(item) && typeof item === "object" && !("language" in item),
    );
    if (elementValues.length) return elementValues;
  }
  if (Array.isArray(element.statements)) return element.statements;
  if (Array.isArray(element.annotations)) return element.annotations;

  const variables = [
    ...(element.inputVariables ?? []),
    ...(element.outputVariables ?? []),
    ...(element.inoutputVariables ?? []),
  ]
    .map((entry) => entry.value)
    .filter((entry): entry is SubmodelElement => Boolean(entry));
  return variables;
}

function formatElementValue(element: SubmodelElement): string | undefined {
  const type = modelTypeOf(element);
  if (type === "MultiLanguageProperty") {
    return languageValue(element.value);
  }
  if (type === "Range") {
    const min = primitiveValue(element.min) ?? "–";
    const max = primitiveValue(element.max) ?? "–";
    return `${min} – ${max}`;
  }
  if (type === "File" || type === "Blob") {
    return primitiveValue(element.value);
  }
  if (type === "ReferenceElement") {
    return referenceValue(
      element.value as { keys?: Array<{ value: string }> } | undefined,
    );
  }
  return primitiveValue(element.value);
}

function parseElement(
  element: SubmodelElement,
  path: string,
  index: number,
): StructuredElement {
  const idShort = element.idShort ?? `Element ${index + 1}`;
  const displayName = displayText(element.displayName);
  const children = childElements(element).map((child, childIndex) =>
    parseElement(child, `${path}.${idShort}`, childIndex),
  );
  return {
    key: `${path}.${idShort}.${index}`,
    idShort,
    label: displayName ?? humanizeIdShort(idShort),
    modelType: modelTypeOf(element),
    value: formatElementValue(element),
    unit: element.unit,
    semanticId: referenceValue(element.semanticId),
    description: displayText(element.description),
    children: children.length ? children : undefined,
  };
}

export function parseSubmodel(submodel: Submodel): StructuredElement[] {
  return (submodel.submodelElements ?? []).map((element, index) =>
    parseElement(element, submodel.idShort ?? "Submodel", index),
  );
}
