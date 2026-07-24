import type {
  ParsedTimeSeries,
  Submodel,
  SubmodelElement,
  TimeSeriesRecord,
} from "../types/aas";

function children(element: SubmodelElement | undefined): SubmodelElement[] {
  return Array.isArray(element?.value)
    ? element.value.filter(
        (entry): entry is SubmodelElement =>
          Boolean(entry) && typeof entry === "object",
      )
    : [];
}

function byIdShort(
  elements: SubmodelElement[],
  idShort: string,
): SubmodelElement | undefined {
  return elements.find((element) => element.idShort === idShort);
}

function stringValue(
  elements: SubmodelElement[],
  idShort: string,
): string | undefined {
  const value = byIdShort(elements, idShort)?.value;
  if (value === undefined || value === null) return undefined;
  return String(value);
}

function numberValue(elements: SubmodelElement[], idShort: string): number {
  const parsed = Number(stringValue(elements, idShort));
  if (!Number.isFinite(parsed)) {
    throw new Error(`TimeSeries record field ${idShort} is missing or invalid.`);
  }
  return parsed;
}

function observedAt(
  sourceTime: number | string,
  segmentLastUpdate: string | undefined,
  receivedAt: Date,
): string {
  const numeric = Number(sourceTime);
  if (Number.isFinite(numeric) && numeric > 1_000_000_000_000) {
    return new Date(numeric).toISOString();
  }
  if (Number.isFinite(numeric) && numeric > 1_000_000_000) {
    return new Date(numeric * 1_000).toISOString();
  }
  if (segmentLastUpdate && !Number.isNaN(Date.parse(segmentLastUpdate))) {
    return new Date(segmentLastUpdate).toISOString();
  }
  return receivedAt.toISOString();
}

function parseRecord(
  record: SubmodelElement,
  lastUpdate: string | undefined,
  receivedAt: Date,
): TimeSeriesRecord {
  const fields = children(record);
  const rawTime = stringValue(fields, "Time") ?? receivedAt.toISOString();
  const sourceTime = Number.isFinite(Number(rawTime)) ? Number(rawTime) : rawTime;
  const jawPosition = numberValue(fields, "JawPosition");
  const gripForce = numberValue(fields, "GripForce");
  const temperature = numberValue(fields, "Temperature");
  const motorCurrent = numberValue(fields, "MotorCurrent");
  const cycleCount = numberValue(fields, "CycleCount");
  const currentState = stringValue(fields, "CurrentState") ?? "UNKNOWN";
  const signature = [
    rawTime,
    jawPosition,
    gripForce,
    temperature,
    motorCurrent,
    cycleCount,
    currentState,
  ].join("|");

  return {
    observedAt: observedAt(sourceTime, lastUpdate, receivedAt),
    sourceTime,
    jawPosition,
    gripForce,
    temperature,
    motorCurrent,
    cycleCount,
    currentState,
    signature,
  };
}

export function parseIdtaTimeSeries(
  submodel: Submodel,
  receivedAt = new Date(),
): ParsedTimeSeries {
  const segments = byIdShort(submodel.submodelElements ?? [], "Segments");
  if (!segments) {
    throw new Error("TimeSeries is missing the Segments collection.");
  }
  const internalSegment = byIdShort(children(segments), "InternalSegment");
  if (!internalSegment) {
    throw new Error("TimeSeries is missing Segments → InternalSegment.");
  }
  const segmentElements = children(internalSegment);
  const records = byIdShort(segmentElements, "Records");
  if (!records) {
    throw new Error(
      "TimeSeries is missing Segments → InternalSegment → Records.",
    );
  }
  const lastUpdate = stringValue(segmentElements, "LastUpdate");
  const recordElements = children(records).filter(
    (element) => element.idShort === "Record",
  );
  if (!recordElements.length) {
    throw new Error(
      "TimeSeries contains no Segments → InternalSegment → Records → Record.",
    );
  }

  return {
    records: recordElements.map((record) =>
      parseRecord(record, lastUpdate, receivedAt),
    ),
    lastUpdate,
    segmentState: stringValue(segmentElements, "State"),
  };
}
