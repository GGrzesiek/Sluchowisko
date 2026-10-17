import { act, fireEvent, render, screen } from "@testing-library/react";
import { ErrorStatusProvider } from "./ErrorStatus";
import { REFRESH_MS } from "./liveRide";
import { ScreenSwitcher } from "./ScreenSwitcher";

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

function answer(status: number, body: unknown) {
  vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(body), { status }));
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
  afterEach(() => {
    window.history.replaceState(null, "", "/");
    vi.useRealTimers();
  });

  it("shows the vehicle's real route once the backend answers", async () => {
    answer(200, ride("Okopowa"));
    openRide();
    expect(await screen.findByText("→ Wiatraczna")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Okopowa/ })).toBeInTheDocument();
  });

  it("refreshes the route every 10 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    answer(200, ride("Okopowa"));
    answer(200, ride("Wola"));
    openRide();
    await screen.findByText("→ Wiatraczna");
    await act(() => vi.advanceTimersByTimeAsync(REFRESH_MS));
    expect(screen.getByRole("img", { name: /teraz Wola/ })).toBeInTheDocument();
  });

  it("keeps the last route and shows a banner when a refresh fails", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    answer(200, ride("Okopowa"));
    answer(503, { code: "no_live_data" });
    openRide();
    await screen.findByText("→ Wiatraczna");
    await act(() => vi.advanceTimersByTimeAsync(REFRESH_MS));
    expect(screen.getByText("Łączymy ponownie…")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Okopowa/ })).toBeInTheDocument();
  });

  it("says when the vehicle is not on the road", async () => {
    answer(404, { code: "vehicle_not_found" });
    openRide();
    expect(await screen.findByRole("heading", { name: "Nie widzimy pojazdu 3122" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wpisz inny numer" }));
    expect(screen.getByLabelText("Numer boczny pojazdu")).toBeInTheDocument();
  });

  it("says when the line has no stories yet", async () => {
    answer(404, { code: "no_route", line: "999" });
    openRide();
    expect(
      await screen.findByRole("heading", { name: "Nie mamy jeszcze historii dla linii 999." }),
    ).toBeInTheDocument();
  });

  it("keeps searching while there is no live data, then moves on", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    answer(503, { code: "no_live_data" });
    answer(200, ride("Okopowa"));
    openRide();
    expect(await screen.findByText("Łączymy ponownie…")).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(REFRESH_MS));
    expect(await screen.findByText("→ Wiatraczna")).toBeInTheDocument();
    expect(screen.queryByText("Łączymy ponownie…")).not.toBeInTheDocument();
  });

  it("stops asking the backend after the ride is cancelled", async () => {
    openRide();
    fireEvent.click(screen.getByRole("button", { name: "Anuluj" }));
    const signal = vi.mocked(fetch).mock.calls[0][1]?.signal;
    expect(signal?.aborted).toBe(true);
  });
});
