import { render, screen } from "@testing-library/react";
import { LineBadge, NowPlayingBar, RouteStrip, StoryCard } from ".";

describe("components", () => {
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
    expect(screen.getByRole("img", { name: /teraz: Krucza/ })).toBeInTheDocument();
  });
});
