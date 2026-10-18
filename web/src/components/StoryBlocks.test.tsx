import { render, screen } from "@testing-library/react";
import { StoryBlocks } from "./StoryBlocks";
import type { StoryBlock, StoryPhoto } from "../types";

const photos: StoryPhoto[] = [
  { alt: "Hala", year: "1936", caption: "Hala Mirowska", credit: "Fot. NN · domena publiczna" },
];

const blocks: StoryBlock[] = [
  { type: "paragraph", text: "Pierwszy akapit." },
  { type: "image", photo: 0 },
  {
    type: "facts",
    items: [
      { value: "1892", label: "OTWARCIE" },
      { value: "800 mm", label: "ROZSTAW" },
      { value: "1973", label: "KONIEC" },
    ],
  },
  { type: "callout", title: "Wyjrzyj przez okno.", text: "Stoi tu dawna stacja." },
  {
    type: "timeline",
    items: [
      { year: "1915", text: "Zniszczenie.", tone: "loss" },
      { year: "dziś", text: "Jedziesz tędy.", tone: "now" },
    ],
  },
];

describe("StoryBlocks", () => {
  it("renders every block type", () => {
    render(<StoryBlocks blocks={blocks} photos={photos} />);
    expect(screen.getByText("Pierwszy akapit.")).toBeInTheDocument();
    expect(screen.getByText("Hala Mirowska")).toBeInTheDocument();
    expect(screen.getByText("800 mm")).toBeInTheDocument();
    expect(screen.getByText("Wyjrzyj przez okno.")).toBeInTheDocument();
    expect(screen.getByText("Jedziesz tędy.")).toBeInTheDocument();
  });

  it("skips an image block that points at a missing photo", () => {
    render(<StoryBlocks blocks={[{ type: "image", photo: 4 }]} photos={photos} />);
    expect(screen.queryByText("Hala Mirowska")).not.toBeInTheDocument();
  });
});
