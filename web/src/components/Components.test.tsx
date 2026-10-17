import { render, screen } from "@testing-library/react";
import { BusAnimation, LineBadge, NowPlayingBar, RouteStrip, StoryCard } from ".";

describe("components", () => {
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
    expect(screen.getAllByText(/^Stop \d+$/).map((e) => e.textContent)).toEqual([
      "Stop 17",
      "Stop 18",
      "Stop 19",
      "Stop 20",
      "Stop 21",
      "Stop 22",
    ]);
  });
});
