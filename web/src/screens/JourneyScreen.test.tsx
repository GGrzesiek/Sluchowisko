import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { JourneyScreen } from "./JourneyScreen";
import type { RideInfo, StoryContent } from "../types";

const ride: RideInfo = {
  vehicle: "4321",
  destination: "Pętla Testowa",
  stops: [
    { name: "Alfa", state: "passed" },
    { name: "Beta", state: "current", hasStory: true },
    { name: "Gamma", state: "next", etaMinutes: 5 },
  ],
};

const story: StoryContent = {
  title: "Historia Bety",
  photos: [
    { alt: "Pierwsze", year: "1936", caption: "Pierwszy podpis", credit: "Autor A · domena publiczna" },
    { alt: "Drugie", year: "1950", caption: "Drugi podpis", credit: "Autor B · CC BY" },
  ],
  body: { format: "plain", text: "Akapit pierwszy.\n\nAkapit drugi." },
  sources: [{ label: "Źródło testowe", href: "https://example.org/zrodlo" }],
};

describe("JourneyScreen", () => {
  it("shows the first photo caption and credit", () => {
    render(<JourneyScreen ride={ride} story={story} />);
    expect(screen.getByText("Pierwszy podpis", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Autor A · domena publiczna")).toBeInTheDocument();
  });

  it("follows the carousel scroll for the caption and dots", () => {
    render(<JourneyScreen ride={ride} story={story} />);
    expect(screen.getByRole("img", { name: "Zdjęcie 1 z 2" })).toBeInTheDocument();
    const scroller = screen.getByRole("img", { name: "Zdjęcie 1 z 2" }).previousElementSibling as HTMLElement;
    Object.defineProperty(scroller, "clientWidth", { value: 300, configurable: true });
    scroller.scrollLeft = 300;
    fireEvent.scroll(scroller);
    expect(screen.getByRole("img", { name: "Zdjęcie 2 z 2" })).toBeInTheDocument();
    expect(screen.getByText("Autor B · CC BY")).toBeInTheDocument();
  });

  it("renders plain text paragraphs and clickable sources", () => {
    render(<JourneyScreen ride={ride} story={story} />);
    expect(screen.getByText("Akapit pierwszy.")).toBeInTheDocument();
    expect(screen.getByText("Akapit drugi.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Źródło testowe/ })).toHaveAttribute("href", "https://example.org/zrodlo");
  });

  it("shows the vehicle and route from the ride data", () => {
    render(<JourneyScreen ride={ride} story={story} />);
    expect(screen.getByLabelText("Pojazd 4321")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /teraz Beta/ })).toBeInTheDocument();
  });

  it("updates the route when new stop data arrives", () => {
    const { rerender } = render(<JourneyScreen ride={ride} story={story} />);
    expect(screen.getByText("5 MIN")).toBeInTheDocument();
    act(() => {
      rerender(
        <JourneyScreen
          ride={{ ...ride, stops: ride.stops.map((s) => (s.etaMinutes ? { ...s, etaMinutes: 3 } : s)) }}
          story={story}
        />,
      );
    });
    expect(screen.getByText("3 MIN")).toBeInTheDocument();
    expect(screen.queryByText("5 MIN")).not.toBeInTheDocument();
  });

  it("calls onClose from the close button", () => {
    const onClose = vi.fn();
    render(<JourneyScreen ride={ride} story={story} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Zakończ przejazd" }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("JourneyScreen swipe hint", () => {
  it("fades the hint out as the page is scrolled", async () => {
    render(<JourneyScreen ride={ride} story={story} />);
    const hint = screen.getByText("Przesuń w górę, by dowiedzieć się więcej").parentElement as HTMLElement;
    expect(hint.style.opacity).toBe("1");
    act(() => {
      Object.defineProperty(window, "scrollY", { value: 100, configurable: true });
      window.dispatchEvent(new Event("scroll"));
    });
    await waitFor(() => expect(hint.style.opacity).toBe("0"));
    Object.defineProperty(window, "scrollY", { value: 0, configurable: true });
  });
});
