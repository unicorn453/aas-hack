import { describe, expect, it } from "vitest";
import { publicSubmodel } from "../test/fixtures";
import { humanizeIdShort, parseSubmodel } from "./submodelParser";

describe("submodel parser", () => {
  it("turns nested AAS elements into readable structured data", () => {
    const parsed = parseSubmodel(publicSubmodel);
    expect(parsed[0]).toMatchObject({
      label: "Manufacturer Name",
      value: "SCHUNK",
    });
    expect(parsed[1].children?.[0]).toMatchObject({
      label: "City Town",
      value: "Lauffen am Neckar",
    });
  });

  it("humanizes generated IDTA idShort values", () => {
    expect(humanizeIdShort("MaintenanceInstructionsForSpecificInterval__00__"))
      .toBe("Maintenance Instructions For Specific Interval");
  });
});
