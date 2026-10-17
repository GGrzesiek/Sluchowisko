import { fireEvent, render, screen } from "@testing-library/react";
import { FindingVehicleScreen } from "./FindingVehicleScreen";

describe("FindingVehicleScreen", () => {
  it("shows the vehicle and the line from a sticker", () => {
    render(<FindingVehicleScreen ride={{ vehicle: "1234", line: "180" }} onCancel={() => {}} />);
    expect(screen.getByLabelText("Pojazd 1234")).toBeInTheDocument();
    expect(screen.getByText("Linia 180")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Łączymy pojazd 1234");
    expect(screen.getByRole("img", { name: "Animacja: ogórek jedzie przez ekran" })).toBeInTheDocument();
  });

  it("leaves out the line when only the vehicle number is known", () => {
    render(<FindingVehicleScreen ride={{ vehicle: "1234" }} onCancel={() => {}} />);
    expect(screen.queryByText(/Linia/)).not.toBeInTheDocument();
  });

  it("cancels the search", () => {
    const onCancel = vi.fn();
    render(<FindingVehicleScreen ride={{ vehicle: "1234" }} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    expect(onCancel).toHaveBeenCalled();
  });
});
