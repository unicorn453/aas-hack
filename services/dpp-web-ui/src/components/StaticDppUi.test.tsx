import { ThemeProvider } from "@mui/material";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { PUBLIC_SUBMODELS } from "../config";
import type { PublicSubmodelResult } from "../data/submodelRepository";
import { publicSubmodel } from "../test/fixtures";
import { createIndustrialTheme } from "../theme";
import { StaticSubmodelGrid } from "./StaticSubmodelGrid";
import { SubmodelViewer } from "./SubmodelViewer";

const results: PublicSubmodelResult[] = PUBLIC_SUBMODELS.map((definition) => ({
  definition,
  data: { ...publicSubmodel, id: definition.id, idShort: definition.title },
}));

function frame(node: ReactNode) {
  return render(
    <ThemeProvider theme={createIndustrialTheme("dark")}>{node}</ThemeProvider>,
  );
}

describe("anonymous static DPP UI", () => {
  it("shows all five public submodels and opens one without authentication", () => {
    const onOpen = vi.fn();
    frame(
      <StaticSubmodelGrid loading={false} submodels={results} onOpen={onOpen} />,
    );
    for (const definition of PUBLIC_SUBMODELS) {
      expect(screen.getByText(definition.title)).toBeInTheDocument();
    }
    fireEvent.click(
      screen.getByRole("button", { name: /open nameplate contents/i }),
    );
    expect(onOpen).toHaveBeenCalledWith(results[0]);
  });

  it("renders structured content and exposes a raw JSON fallback", () => {
    frame(<SubmodelViewer selected={results[0]} onClose={() => undefined} />);
    expect(screen.getByText("Manufacturer Name")).toBeInTheDocument();
    expect(screen.getByText("SCHUNK")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /view raw json/i }));
    expect(screen.getByLabelText("Raw submodel JSON")).toHaveTextContent(
      "ManufacturerName",
    );
  });
});
