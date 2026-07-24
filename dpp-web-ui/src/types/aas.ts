export interface ReferenceKey {
  type?: string;
  value: string;
}

export interface AasReference {
  type?: string;
  keys?: ReferenceKey[];
}

export interface LangString {
  language?: string;
  text?: string;
}

export interface SpecificAssetId {
  name?: string;
  value?: string;
  semanticId?: AasReference;
}

export interface AssetInformation {
  assetKind?: string;
  globalAssetId?: string;
  assetType?: string;
  specificAssetIds?: SpecificAssetId[];
  defaultThumbnail?: {
    path?: string;
    contentType?: string;
  };
}

export interface AssetAdministrationShell {
  modelType?: string;
  id: string;
  idShort?: string;
  displayName?: LangString[];
  description?: LangString[];
  assetInformation?: AssetInformation;
  submodels?: AasReference[];
  [key: string]: unknown;
}

export interface AasDescriptor {
  id: string;
  idShort?: string;
  displayName?: LangString[];
  endpoints?: unknown[];
  [key: string]: unknown;
}

export interface SubmodelElement {
  modelType?: string | { name?: string };
  idShort?: string;
  displayName?: LangString[];
  description?: LangString[];
  semanticId?: AasReference;
  value?: unknown;
  valueType?: string;
  unit?: string;
  contentType?: string;
  min?: unknown;
  max?: unknown;
  statements?: SubmodelElement[];
  annotations?: SubmodelElement[];
  inputVariables?: Array<{ value?: SubmodelElement }>;
  outputVariables?: Array<{ value?: SubmodelElement }>;
  inoutputVariables?: Array<{ value?: SubmodelElement }>;
  [key: string]: unknown;
}

export interface Submodel {
  modelType?: string;
  kind?: string;
  id: string;
  idShort?: string;
  displayName?: LangString[];
  description?: LangString[];
  semanticId?: AasReference;
  submodelElements?: SubmodelElement[];
  [key: string]: unknown;
}

export interface SubmodelDescriptor {
  id: string;
  idShort?: string;
  semanticId?: AasReference;
  endpoints?: unknown[];
  [key: string]: unknown;
}

export interface CollectionResponse<T> {
  result: T[];
  paging_metadata?: Record<string, unknown>;
}

export interface AssetOverview {
  name: string;
  manufacturer: string;
  productFamily: string;
  assetKind: string;
  assetType: string;
  globalAssetId: string;
  aasId: string;
  thumbnail?: string;
}

export interface StructuredElement {
  key: string;
  label: string;
  idShort: string;
  modelType: string;
  value?: string;
  unit?: string;
  semanticId?: string;
  description?: string;
  children?: StructuredElement[];
}

export interface TimeSeriesRecord {
  observedAt: string;
  sourceTime: number | string;
  jawPosition: number;
  gripForce: number;
  temperature: number;
  motorCurrent: number;
  cycleCount: number;
  currentState: string;
  signature: string;
}

export interface ParsedTimeSeries {
  records: TimeSeriesRecord[];
  lastUpdate?: string;
  segmentState?: string;
}
