import { fireEvent, render, screen } from "@testing-library/react";
import { ScreenSwitcher } from "./ScreenSwitcher";

vi.mock("qr-scanner", () => ({
  default: vi.fn(function () {
    return { start: () => new Promise(() => {}), stop: vi.fn(), destroy: vi.fn() };
  }),
}));

function openAt(url: string) {
  window.history.replaceState(null, "", url);
  render(<ScreenSwitcher />);
}

describe("ScreenSwitcher", () => {
  afterEach(() => window.history.replaceState(null, "", "/"));

  it("opens the loading screen straight from a QR sticker link", () => {
    openAt("/?line=180&vehicle=1234");
    expect(screen.getByRole("heading", { name: "Szukamy Twojego autobusu…" })).toBeInTheDocument();
    expect(screen.getByText(/Pojazd 1234, linia 180/)).toBeInTheDocument();
  });

  it("clears the link when the ride is cancelled", () => {
    openAt("/?line=180&vehicle=1234");
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    expect(screen.getByRole("button", { name: "Wpisz numer boczny pojazdu" })).toBeInTheDocument();
    expect(window.location.search).toBe("");
  });

  it("leads from the start screen to manual entry and to the scanner", () => {
    openAt("/");
    fireEvent.click(screen.getByRole("button", { name: "Wpisz numer boczny pojazdu" }));
    expect(screen.getByRole("heading", { name: "Którym autobusem lub tramwajem jedziesz?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wstecz" }));
    fireEvent.click(screen.getByRole("button", { name: "Zeskanuj kod QR" }));
    expect(screen.getByRole("heading", { name: "Zeskanuj kod z naklejki" })).toBeInTheDocument();
  });
});
