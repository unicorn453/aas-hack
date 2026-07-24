import type { Submodel } from "../types/aas";

function property(idShort: string, value: string) {
  return { modelType: "Property", idShort, value, valueType: "xs:string" };
}

export const publicSubmodel: Submodel = {
  modelType: "Submodel",
  id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/nameplate",
  idShort: "Nameplate",
  submodelElements: [
    {
      modelType: "MultiLanguageProperty",
      idShort: "ManufacturerName",
      value: [{ language: "en", text: "SCHUNK" }],
    },
    {
      modelType: "SubmodelElementCollection",
      idShort: "AddressInformation",
      value: [property("CityTown", "Lauffen am Neckar")],
    },
  ],
};

export const timeSeriesSubmodel: Submodel = {
  modelType: "Submodel",
  id: "https://example.org/submodels/schunk/pgn-plus-p-64-1/timeseries",
  idShort: "TimeSeries",
  submodelElements: [
    {
      modelType: "SubmodelElementCollection",
      idShort: "Segments",
      value: [
        {
          modelType: "SubmodelElementCollection",
          idShort: "InternalSegment",
          value: [
            property("State", "RUNNING"),
            property("LastUpdate", "2026-07-23T20:00:00Z"),
            {
              modelType: "SubmodelElementCollection",
              idShort: "Records",
              value: [
                {
                  modelType: "SubmodelElementCollection",
                  idShort: "Record",
                  value: [
                    property("Time", "1753300800"),
                    property("JawPosition", "24.5"),
                    property("GripForce", "42.25"),
                    property("Temperature", "26.1"),
                    property("MotorCurrent", "1.45"),
                    property("CycleCount", "18"),
                    property("CurrentState", "GRIPPING"),
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};
