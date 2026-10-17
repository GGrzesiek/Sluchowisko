import { fireEvent, render, screen } from "@testing-library/react";
import { ErrorStatusProvider } from "./ErrorStatus";
import { ScreenSwitcher } from "./ScreenSwitcher";

vi.mock("qr-scanner", () => ({
  default: vi.fn(function () {
    return { start: () => new Promise(() => {}), stop: vi.fn(), destroy: vi.fn() };
  }),
}));

function openAt(url: string) {
  window.history.replaceState(null, "", url);
  render(
    <ErrorStatusProvider>
      <ScreenSwitcher />
    </ErrorStatusProvider>,
  );
}

describe("ScreenSwitcher", () => {
  afterEach(() => window.history.replaceState(null, "", "/"));

  it("shows the debug page with links to every screen at /debug", () => {
    openAt("/debug");
    expect(screen.getByRole("heading", { name: "Ekrany" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Wpisz numer pojazdu/ })).toHaveAttribute("href", "#/manual");
    expect(screen.getByRole("link", { name: /Powitanie/ })).toHaveAttribute("href", "/");
  });

  it("opens the loading screen straight from a QR sticker link", () => {
    openAt("/?line=180&vehicle=1234");
    expect(screen.getByRole("heading", { name: "Szukamy Twojego autobusu…" })).toBeInTheDocument();
    expect(screen.getByLabelText("Pojazd 1234")).toBeInTheDocument();
    expect(screen.getByText("Linia 180")).toBeInTheDocument();
  });

  it("clears the link when the ride is cancelled", () => {
    openAt("/?line=180&vehicle=1234");
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    expect(screen.getByRole("button", { name: "Wpisz numer boczny pojazdu" })).toBeInTheDocument();
    expect(window.location.search).toBe("");
  });

  it("focuses the number field as soon as manual entry opens", () => {
    openAt("/");
    fireEvent.click(screen.getByRole("button", { name: "Wpisz numer boczny pojazdu" }));
    expect(screen.getByLabelText("Numer boczny pojazdu")).toHaveFocus();
  });

  it("finds the vehicle typed on the manual entry screen", () => {
    openAt("/");
    fireEvent.click(screen.getByRole("button", { name: "Wpisz numer boczny pojazdu" }));
    fireEvent.change(screen.getByLabelText("Numer boczny pojazdu"), { target: { value: "1234" } });
    fireEvent.click(screen.getByRole("button", { name: "Znajdź mój pojazd" }));
    expect(screen.getByRole("heading", { name: "Szukamy Twojego autobusu…" })).toBeInTheDocument();
    expect(screen.getByLabelText("Pojazd 1234")).toBeInTheDocument();
  });

  it("keeps the gallery screen previews working", () => {
    openAt("/#/manual");
    expect(screen.getByRole("heading", { name: "Którym autobusem lub tramwajem jedziesz?" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Wpisz numer boczny pojazdu" })).not.toBeInTheDocument();
  });

  it("leads from the start screen to manual entry and to the scanner", async () => {
    openAt("/");
    fireEvent.click(screen.getByRole("button", { name: "Wpisz numer boczny pojazdu" }));
    expect(screen.getByRole("heading", { name: "Którym autobusem lub tramwajem jedziesz?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wstecz" }));
    fireEvent.click(await screen.findByRole("button", { name: "Zeskanuj kod QR" }));
    expect(screen.getByRole("heading", { name: "Zeskanuj kod z naklejki" })).toBeInTheDocument();
  });
});
