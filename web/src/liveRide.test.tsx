import { act, fireEvent, render, screen } from "@testing-library/react";
import { ErrorStatusProvider } from "./ErrorStatus";
import { MIN_LOADING_MS } from "./liveRide";
import { ScreenSwitcher } from "./ScreenSwitcher";
import { FakeWebSocket } from "./test-setup";

vi.mock("qr-scanner", () => ({
  default: vi.fn(function () {
    return { start: () => new Promise(() => {}), stop: vi.fn(), destroy: vi.fn() };
  }),
}));

function ride(current: string) {
  return {
    vehicle: "3122",
    line: "22",
    destination: "Wiatraczna",
    stops: [
      { name: "Okopowa", state: current === "Okopowa" ? "current" : "passed" },
      { name: "Wola", state: current === "Wola" ? "current" : "next", etaMinutes: 2 },
    ],
  };
}

const socket = () => FakeWebSocket.instances[FakeWebSocket.instances.length - 1];

async function answer(type: string, data: unknown) {
  act(() => socket().receive(type, data));
  await act(() => vi.advanceTimersByTimeAsync(MIN_LOADING_MS));
}

function openRide() {
  window.history.replaceState(null, "", "/?line=22&vehicle=3122");
  render(
    <ErrorStatusProvider>
      <ScreenSwitcher />
    </ErrorStatusProvider>,
  );
}

describe("live ride", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    window.history.replaceState(null, "", "/");
    vi.useRealTimers();
  });

  it("connects a WebSocket for the vehicle", () => {
    openRide();
    expect(socket().url).toMatch(/\/ws\/ride\/3122\/$/);
  });

  it("shows the vehicle's real route once the backend pushes it", async () => {
    openRide();
    await answer("route", ride("Okopowa"));
    expect(await screen.findByText("→ Wiatraczna")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Okopowa/ })).toBeInTheDocument();
  });

  it("updates the route when the backend pushes a new one", async () => {
    openRide();
    await answer("route", ride("Okopowa"));
    await screen.findByText("→ Wiatraczna");
    await answer("route", ride("Wola"));
    expect(screen.getByRole("img", { name: /teraz Wola/ })).toBeInTheDocument();
  });

  it("keeps the last route and shows a banner when the backend loses the position", async () => {
    openRide();
    await answer("route", ride("Okopowa"));
    await screen.findByText("→ Wiatraczna");
    await answer("error", { code: "no_live_data" });
    expect(screen.getByText("Łączymy ponownie…")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Okopowa/ })).toBeInTheDocument();
  });

  it("reconnects after the connection drops and recovers", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    openRide();
    await answer("route", ride("Okopowa"));
    await screen.findByText("→ Wiatraczna");
    const first = socket();
    act(() => first.drop());
    expect(screen.getByText("Łączymy ponownie…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(1_000));
    expect(FakeWebSocket.instances).toHaveLength(3);
    await answer("route", ride("Wola"));
    expect(screen.queryByText("Łączymy ponownie…")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Wola/ })).toBeInTheDocument();
  });

  it("says when the vehicle is not on the road", async () => {
    openRide();
    await answer("error", { code: "vehicle_not_found" });
    expect(await screen.findByRole("heading", { name: "Nie widzimy tego pojazdu" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Pojazd 3122" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wpisz inny numer" }));
    expect(screen.getByLabelText("Numer taborowy pojazdu")).toBeInTheDocument();
  });

  it("says when the line has no stories yet", async () => {
    openRide();
    await answer("error", { code: "no_route", line: "999" });
    expect(await screen.findByRole("heading", { name: "Nie mamy jeszcze historii dla tej linii" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Linia 999" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Linie z historiami" })).toHaveTextContent("2218179169117");
  });

  it("keeps waiting while there is no live data, then moves on", async () => {
    openRide();
    await answer("error", { code: "no_live_data" });
    expect(await screen.findByText("Łączymy ponownie…")).toBeInTheDocument();
    await answer("route", ride("Okopowa"));
    expect(await screen.findByText("→ Wiatraczna")).toBeInTheDocument();
    expect(screen.queryByText("Łączymy ponownie…")).not.toBeInTheDocument();
  });

  it("ignores garbage from the server", () => {
    openRide();
    act(() => socket().onmessage?.({ data: "not json" }));
    act(() => socket().onmessage?.({ data: new ArrayBuffer(1) }));
    act(() => socket().receive("route", { nope: true }));
    expect(screen.queryByText("→ Wiatraczna")).not.toBeInTheDocument();
  });

  it("starts the story when the passenger taps Zaczynamy and stops it when the ride ends", async () => {
    openRide();
    await answer("route", ride("Okopowa"));
    fireEvent.click(await screen.findByRole("button", { name: "Zaczynamy" }));

    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: "Pauza" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Zakończ przejazd" }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
  });

  it("silences the story and clears the lock screen when the journey is left with browser back", async () => {
    openRide();
    await answer("route", ride("Okopowa"));
    fireEvent.click(await screen.findByRole("button", { name: "Zaczynamy" }));
    await screen.findByRole("button", { name: "Pauza" });
    const player = document.querySelector("audio") as HTMLAudioElement;
    expect(player.getAttribute("src")).not.toBeNull();

    act(() => window.history.back());
    await act(() => vi.advanceTimersByTimeAsync(50));

    expect(screen.queryByRole("button", { name: "Zakończ przejazd" })).not.toBeInTheDocument();
    expect(player.hasAttribute("src")).toBe(false);
  });

  it("keeps the loading screen up for a moment when the answer comes at once", async () => {
    openRide();
    act(() => socket().receive("error", { code: "vehicle_not_found" }));
    await act(() => vi.advanceTimersByTimeAsync(MIN_LOADING_MS - 100));
    expect(screen.getByRole("heading", { name: "Szukamy Twojego autobusu…" })).toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(100));
    expect(screen.getByRole("heading", { name: "Nie widzimy tego pojazdu" })).toBeInTheDocument();
  });

  it("does not hold a slow answer any longer", async () => {
    openRide();
    await act(() => vi.advanceTimersByTimeAsync(MIN_LOADING_MS * 2));
    act(() => socket().receive("error", { code: "vehicle_not_found" }));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(screen.getByRole("heading", { name: "Nie widzimy tego pojazdu" })).toBeInTheDocument();
  });

  it("closes the socket after the ride is cancelled", () => {
    openRide();
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    expect(socket().closed).toBe(true);
  });

  it("pings the server and reconnects when it does not answer", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    openRide();
    const first = socket();
    act(() => first.open());
    await act(() => vi.advanceTimersByTimeAsync(20_000));
    expect(first.sent).toEqual([JSON.stringify({ type: "ping" })]);
    await act(() => vi.advanceTimersByTimeAsync(10_000));
    expect(first.closed).toBe(true);
  });

  it("shows the story the backend sends for the current stop on the journey screen", async () => {
    openRide();
    await answer("route", ride("Okopowa"));
    fireEvent.click(await screen.findByRole("button", { name: "Zaczynamy" }));
    await screen.findByRole("button", { name: "Zakończ przejazd" });
    await answer("location", {
      groupId: "5002",
      story: {
        groupId: "5002",
        title: "Cmentarz Powązkowski",
        photos: [{ alt: "Brama", year: "1900", caption: "Brama główna", credit: "Fot. NN · domena publiczna" }],
        body: { format: "plain", text: "Tekst o cmentarzu." },
        sources: [{ label: "Wikipedia", href: "https://pl.wikipedia.org/wiki/Cmentarz" }],
      },
    });
    expect((await screen.findAllByText("Cmentarz Powązkowski")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Hala Mirowska")).not.toBeInTheDocument();
  });
});
