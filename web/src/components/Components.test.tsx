import { render, screen } from "@testing-library/react";
import { BusAnimation, ErrorBanner, LineBadge, NowPlayingBar, RouteStrip, StoryCard } from ".";

describe("components", () => {
  it("tells the passenger the story goes on while the vehicle position is lost", () => {
    render(<ErrorBanner error={{ kind: "positionLost", line: "180", lastStop: "Stare Miasto" }} />);
    expect(screen.getByRole("status")).toHaveTextContent("Łączymy ponownie…");
    expect(screen.getByRole("status")).toHaveTextContent("Historia gra dalej. Przystanki mogą się chwilę spóźniać.");
    expect(screen.getByRole("img", { name: "Autobus 180" })).toBeInTheDocument();
    expect(screen.getByText("Ostatni znany przystanek: Stare Miasto")).toBeInTheDocument();
  });

  it("leaves out the last stop when none is known yet", () => {
    render(<ErrorBanner error={{ kind: "positionLost" }} />);
    expect(screen.queryByText(/Ostatni znany przystanek/)).not.toBeInTheDocument();
  });

  it.each([
    ["offline", "Brak internetu"],
    ["dataUnavailable", "Nie udało się wczytać danych"],
    ["unexpected", "Coś poszło nie tak"],
  ] as const)("names the %s error", (kind, title) => {
    render(<ErrorBanner error={{ kind }} />);
    expect(screen.getByRole("status")).toHaveTextContent(title);
  });

  it("describes the bus animation for assistive tech", () => {
    render(<BusAnimation />);
    expect(screen.getByRole("img", { name: "Animacja: ogórek jedzie przez ekran" })).toBeInTheDocument();
  });

  it("labels a line badge for assistive tech", () => {
    render(<LineBadge line="180" kind="bus" />);
    expect(screen.getByRole("img", { name: "Autobus 180" })).toBeInTheDocument();
  });

  it("shows playback state on the now-playing bar", () => {
    render(<NowPlayingBar title="Hala" playing progress={0.5} elapsedLabel="0:48" totalLabel="1:32" />);
    expect(screen.getByRole("button", { name: "Pauza" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50");
  });

  it("renders a skipped story as a button when clickable", () => {
    render(<StoryCard state="skipped" title="Bazar" thumb={{ variant: "map" }} onClick={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent("Pominięta");
  });

  it("describes the route for assistive tech", () => {
    render(
      <RouteStrip
        stops={[
          { name: "Centrum", state: "passed" },
          { name: "Krucza", state: "current" },
        ]}
      />,
    );
    expect(screen.getByRole("img", { name: /teraz Krucza/ })).toBeInTheDocument();
  });

  it("shows only the last and next stops around the current one", () => {
    const stops = Array.from({ length: 50 }, (_, i) => ({
      name: `Stop ${i}`,
      state: i < 20 ? ("passed" as const) : i === 20 ? ("current" as const) : ("next" as const),
    }));
    render(<RouteStrip stops={stops} before={3} after={2} />);
    const visible = screen.getAllByText(/^Stop \d+$/).filter((e) => !e.closest('[aria-hidden="true"]'));
    expect(visible.map((e) => e.textContent)).toEqual([
      "Stop 17",
      "Stop 18",
      "Stop 19",
      "Stop 20",
      "Stop 21",
      "Stop 22",
    ]);
  });

  it("keeps stops that are sliding in or out in the page, hidden", () => {
    const stops = Array.from({ length: 50 }, (_, i) => ({
      name: `Stop ${i}`,
      state: i < 20 ? ("passed" as const) : i === 20 ? ("current" as const) : ("next" as const),
    }));
    render(<RouteStrip stops={stops} before={3} after={2} />);
    const hidden = screen.getAllByText(/^Stop \d+$/).filter((e) => e.closest('[aria-hidden="true"]'));
    expect(hidden.map((e) => e.textContent)).toEqual(["Stop 16", "Stop 23"]);
  });
});
