import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ErrorStatusProvider } from "./ErrorStatus";
import { MIN_LOADING_MS } from "./liveRide";
import { ScreenSwitcher } from "./ScreenSwitcher";
import { FakeWebSocket } from "./test-setup";

vi.mock("qr-scanner", () => ({
  default: vi.fn(function () {
    return { start: () => new Promise(() => {}), stop: vi.fn(), destroy: vi.fn() };
  }),
}));

const ride = {
  vehicle: "3122",
  line: "22",
  destination: "Wiatraczna",
  stops: [{ name: "Okopowa", state: "current" }],
};

const socket = () => FakeWebSocket.instances[FakeWebSocket.instances.length - 1];

async function answer(type: string, data: unknown) {
  act(() => socket().receive(type, data));
  await act(() => vi.advanceTimersByTimeAsync(MIN_LOADING_MS));
}
const heading = (name: string) => screen.findByRole("heading", { name });
const MANUAL = "Którym autobusem lub tramwajem jedziesz?";
const SEARCHING = "Szukamy Twojego autobusu…";

async function back() {
  await act(async () => {
    window.history.back();
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
}

async function forward() {
  await act(async () => {
    window.history.forward();
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
}

function open(url = "/") {
  window.history.replaceState(null, "", url);
  render(
    <ErrorStatusProvider>
      <ScreenSwitcher />
    </ErrorStatusProvider>,
  );
}

async function typeVehicle(number: string) {
  fireEvent.click(screen.getByRole("button", { name: "Wpisz numer taborowy pojazdu" }));
  fireEvent.change(screen.getByLabelText("Numer taborowy pojazdu"), { target: { value: number } });
  fireEvent.click(screen.getByRole("button", { name: "Znajdź mój pojazd" }));
  await heading(SEARCHING);
}

describe("navigation history", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    window.history.replaceState(null, "", "/");
    vi.useRealTimers();
  });

  it("goes back through every screen of a ride with the browser back button", async () => {
    open();
    await typeVehicle("3122");
    await answer("route", ride);
    fireEvent.click(await screen.findByRole("button", { name: "Zaczynamy" }));
    expect(await screen.findByRole("button", { name: "Zakończ przejazd" })).toBeInTheDocument();

    await back();
    expect(await screen.findByRole("button", { name: "Zaczynamy" })).toBeInTheDocument();
    await back();
    expect(await heading(MANUAL)).toBeInTheDocument();
    await back();
    expect(await screen.findByRole("button", { name: "Wpisz numer taborowy pojazdu" })).toBeInTheDocument();
  });

  it("does not trap the user on the searching screen after the vehicle is found", async () => {
    open();
    await typeVehicle("3122");
    await answer("route", ride);
    await screen.findByRole("button", { name: "Zaczynamy" });
    await back();
    expect(screen.queryByRole("heading", { name: SEARCHING })).not.toBeInTheDocument();
    expect(await heading(MANUAL)).toBeInTheDocument();
  });

  it("goes forward again to the ride after going back", async () => {
    open();
    await typeVehicle("3122");
    await answer("route", ride);
    await screen.findByRole("button", { name: "Zaczynamy" });
    await back();
    await heading(MANUAL);
    await forward();
    expect(await screen.findByRole("button", { name: "Zaczynamy" })).toBeInTheDocument();
    expect(screen.getByText("→ Wiatraczna")).toBeInTheDocument();
  });

  it("lets the user go back from a dead end to the number entry", async () => {
    open();
    await typeVehicle("4040");
    await answer("error", { code: "vehicle_not_found" });
    await heading("Nie widzimy tego pojazdu");
    await back();
    expect(await heading(MANUAL)).toBeInTheDocument();
  });

  it("the on-screen back and cancel buttons use the same history", async () => {
    open();
    await typeVehicle("3122");
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    expect(await heading(MANUAL)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wstecz" }));
    expect(await screen.findByRole("button", { name: "Wpisz numer taborowy pojazdu" })).toBeInTheDocument();
  });

  it("falls back to the start screen when there is nothing to go back to", async () => {
    open("/?line=22&vehicle=3122");
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    expect(await screen.findByRole("button", { name: "Wpisz numer taborowy pojazdu" })).toBeInTheDocument();
    expect(window.location.search).toBe("");
  });

  it("restores the screen from history state after a reload", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: "Wpisz numer taborowy pojazdu" }));
    await heading(MANUAL);
    document.body.innerHTML = "";
    await waitFor(() => expect(window.history.state).toMatchObject({ screen: { name: "vehicleNumber" } }));
  });
});
