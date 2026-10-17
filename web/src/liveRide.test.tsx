import { act, fireEvent, render, screen } from "@testing-library/react";
import { ErrorStatusProvider } from "./ErrorStatus";
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

function openRide() {
  window.history.replaceState(null, "", "/?line=22&vehicle=3122");
  render(
    <ErrorStatusProvider>
      <ScreenSwitcher />
    </ErrorStatusProvider>,
  );
}

describe("live ride", () => {
  afterEach(() => {
    window.history.replaceState(null, "", "/");
    vi.useRealTimers();
  });

  it("connects a WebSocket for the vehicle", () => {
    openRide();
    expect(socket().url).toMatch(/\/ws\/ride\/3122\/\?device_id=.+/);
  });

  it("shows the vehicle's real route once the backend pushes it", async () => {
    openRide();
    act(() => socket().receive("route", ride("Okopowa")));
    expect(await screen.findByText("→ Wiatraczna")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Okopowa/ })).toBeInTheDocument();
  });

  it("updates the route when the backend pushes a new one", async () => {
    openRide();
    act(() => socket().receive("route", ride("Okopowa")));
    await screen.findByText("→ Wiatraczna");
    act(() => socket().receive("route", ride("Wola")));
    expect(screen.getByRole("img", { name: /teraz Wola/ })).toBeInTheDocument();
  });

  it("keeps the last route and shows a banner when the backend loses the position", async () => {
    openRide();
    act(() => socket().receive("route", ride("Okopowa")));
    await screen.findByText("→ Wiatraczna");
    act(() => socket().receive("error", { code: "no_live_data" }));
    expect(screen.getByText("Łączymy ponownie…")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Okopowa/ })).toBeInTheDocument();
  });

  it("reconnects after the connection drops and recovers", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    openRide();
    act(() => socket().receive("route", ride("Okopowa")));
    await screen.findByText("→ Wiatraczna");
    const first = socket();
    act(() => first.drop());
    expect(screen.getByText("Łączymy ponownie…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(1_000));
    expect(FakeWebSocket.instances).toHaveLength(3);
    act(() => socket().receive("route", ride("Wola")));
    expect(screen.queryByText("Łączymy ponownie…")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Wola/ })).toBeInTheDocument();
  });

  it("says when the vehicle is not on the road", async () => {
    openRide();
    act(() => socket().receive("error", { code: "vehicle_not_found" }));
    expect(await screen.findByRole("heading", { name: "Nie widzimy pojazdu 3122" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wpisz inny numer" }));
    expect(screen.getByLabelText("Numer boczny pojazdu")).toBeInTheDocument();
  });

  it("says when the line has no stories yet", async () => {
    openRide();
    act(() => socket().receive("error", { code: "no_route", line: "999" }));
    expect(
      await screen.findByRole("heading", { name: "Nie mamy jeszcze historii dla linii 999." }),
    ).toBeInTheDocument();
  });

  it("keeps waiting while there is no live data, then moves on", async () => {
    openRide();
    act(() => socket().receive("error", { code: "no_live_data" }));
    expect(await screen.findByText("Łączymy ponownie…")).toBeInTheDocument();
    act(() => socket().receive("route", ride("Okopowa")));
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
});
