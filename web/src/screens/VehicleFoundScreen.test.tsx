import { fireEvent, render, screen } from "@testing-library/react";
import { VehicleFoundScreen } from "./VehicleFoundScreen";
import type { RideInfo } from "../types";

const ride: RideInfo = {
  vehicle: "4321",
  destination: "Pętla Testowa",
  stops: [
    { name: "Alfa", state: "passed" },
    { name: "Beta", state: "current", hasStory: true },
    { name: "Gamma", state: "next", etaMinutes: 5 },
    { name: "Delta", state: "next" },
  ],
};

describe("VehicleFoundScreen", () => {
  it("shows vehicle number and destination from the ride data", () => {
    render(<VehicleFoundScreen ride={ride} onStart={() => {}} />);
    expect(screen.getByLabelText("Pojazd 4321")).toBeInTheDocument();
    expect(screen.getByText("→ Pętla Testowa")).toBeInTheDocument();
  });

  it("describes the stops in the aria-label from the data", () => {
    render(<VehicleFoundScreen ride={ride} onStart={() => {}} />);
    expect(
      screen.getByRole("img", {
        name: "Przystanki: poprzednie Alfa; teraz Beta; następne Gamma za 5 minut, Delta",
      }),
    ).toBeInTheDocument();
  });

  it("renders ETA and story marker only where the data has them", () => {
    render(<VehicleFoundScreen ride={ride} onStart={() => {}} />);
    expect(screen.getByText("5 MIN")).toBeInTheDocument();
    expect(screen.getAllByText("MIN", { exact: false })).toHaveLength(1);
  });

  it("starts the ride", () => {
    const onStart = vi.fn();
    render(<VehicleFoundScreen ride={ride} onStart={onStart} />);
    fireEvent.click(screen.getByRole("button", { name: "Zaczynamy" }));
    expect(onStart).toHaveBeenCalled();
  });
});
