import { fireEvent, render, screen } from "@testing-library/react";
import { ManualEntryScreen, isValidVehicleNumber, sanitizeVehicleNumber } from "./ManualEntryScreen";

function setup() {
  const onBack = vi.fn();
  const onSubmit = vi.fn();
  render(<ManualEntryScreen onBack={onBack} onSubmit={onSubmit} />);
  return {
    onBack,
    onSubmit,
    input: screen.getByLabelText("Numer boczny pojazdu"),
    button: screen.getByRole("button", { name: "Znajdź mój pojazd" }),
  };
}

describe("validation helpers", () => {
  it("keeps only the first four digits", () => {
    expect(sanitizeVehicleNumber("12a3-4567")).toBe("1234");
  });

  it("accepts exactly four digits", () => {
    expect(isValidVehicleNumber("1234")).toBe(true);
    expect(isValidVehicleNumber("123")).toBe(false);
    expect(isValidVehicleNumber("12345")).toBe(false);
    expect(isValidVehicleNumber("12a4")).toBe(false);
  });
});

describe("ManualEntryScreen", () => {
  it("renders the heading and numeric input", () => {
    const { input } = setup();
    expect(screen.getByRole("heading", { name: "Którym autobusem lub tramwajem jedziesz?" })).toBeInTheDocument();
    expect(input).toHaveAttribute("inputmode", "numeric");
    expect(input).toHaveAttribute("placeholder", "np. 1234");
    expect(screen.getByText("Szukaj nad drzwiami albo przy kabinie kierowcy. To 4 cyfry.")).toBeInTheDocument();
  });

  it("disables the button until exactly four digits are entered", () => {
    const { input, button } = setup();
    expect(button).toBeDisabled();
    fireEvent.change(input, { target: { value: "123" } });
    expect(button).toBeDisabled();
    fireEvent.change(input, { target: { value: "1234" } });
    expect(button).toBeEnabled();
  });

  it("strips non-digit characters", () => {
    const { input } = setup();
    fireEvent.change(input, { target: { value: "1a2b" } });
    expect(input).toHaveValue("12");
  });

  it("submits the number when the form is submitted (Enter)", () => {
    const { input, onSubmit } = setup();
    fireEvent.change(input, { target: { value: "1234" } });
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).toHaveBeenCalledWith("1234");
  });

  it("does not submit an incomplete number", () => {
    const { input, onSubmit } = setup();
    fireEvent.change(input, { target: { value: "12" } });
    fireEvent.submit(input.closest("form")!);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("goes back", () => {
    const { onBack } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Wstecz" }));
    expect(onBack).toHaveBeenCalled();
  });
});
