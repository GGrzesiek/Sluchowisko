import { act, fireEvent, render, screen } from "@testing-library/react";
import { clock, NarrationProvider, useNarration } from "./Narration";
import type { StoryContent } from "./types";

const story: StoryContent = {
  title: "Historia testowa",
  photos: [{ alt: "Zdjęcie", year: "1936", caption: "Podpis", credit: "Autor" }],
  body: { format: "plain", text: "Tekst." },
  sources: [],
  audio: "/audio/test.m4a",
};

function Controls() {
  const narration = useNarration();
  return (
    <>
      <button onClick={() => narration.start(story)}>start</button>
      <button onClick={() => narration.stop()}>stop</button>
      <output>{narration.playing ? "gra" : "cisza"}</output>
    </>
  );
}

const player = () => document.querySelector("audio") as HTMLAudioElement;

describe("clock", () => {
  it("shows minutes and seconds", () => {
    expect(clock(0)).toBe("00:00");
    expect(clock(125.9)).toBe("02:05");
    expect(clock(Number.NaN)).toBe("--:--");
    expect(clock(Number.POSITIVE_INFINITY)).toBe("--:--");
  });
});

describe("NarrationProvider", () => {
  it("starts playing inside the tap, so phones allow the sound", () => {
    render(<Controls />, { wrapper: NarrationProvider });
    fireEvent.click(screen.getByRole("button", { name: "start" }));

    expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1);
    expect(player().getAttribute("src")).toBe("/audio/test.m4a");
    expect(screen.getByRole("status")).toHaveTextContent("gra");
  });

  it("stops and forgets the story", () => {
    render(<Controls />, { wrapper: NarrationProvider });
    fireEvent.click(screen.getByRole("button", { name: "start" }));
    fireEvent.click(screen.getByRole("button", { name: "stop" }));

    expect(screen.getByRole("status")).toHaveTextContent("cisza");
    expect(player().hasAttribute("src")).toBe(false);
  });

  it("shows the story as paused when the browser refuses to play", async () => {
    vi.mocked(HTMLMediaElement.prototype.play).mockImplementationOnce(() => Promise.reject(new Error("blocked")));
    render(<Controls />, { wrapper: NarrationProvider });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "start" }));
    });

    expect(screen.getByRole("status")).toHaveTextContent("cisza");
  });

  it("needs the provider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Controls />)).toThrow("useNarration needs NarrationProvider");
  });
});
