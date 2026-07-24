import { describe, expect, it } from "vitest";
import { timeSeriesSubmodel } from "../test/fixtures";
import { parseIdtaTimeSeries } from "./timeSeriesParser";

describe("parseIdtaTimeSeries", () => {
  it("reads the required IDTA internal segment record path", () => {
    const parsed = parseIdtaTimeSeries(timeSeriesSubmodel);
    expect(parsed.segmentState).toBe("RUNNING");
    expect(parsed.lastUpdate).toBe("2026-07-23T20:00:00Z");
    expect(parsed.records).toHaveLength(1);
    expect(parsed.records[0]).toMatchObject({
      jawPosition: 24.5,
      gripForce: 42.25,
      temperature: 26.1,
      motorCurrent: 1.45,
      cycleCount: 18,
      currentState: "GRIPPING",
    });
  });

  it("rejects a submodel without Segments", () => {
    expect(() =>
      parseIdtaTimeSeries({
        id: "missing",
        submodelElements: [],
      }),
    ).toThrow(/Segments/);
  });
});
