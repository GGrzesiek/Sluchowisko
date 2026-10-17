import { Prose } from "./Article";
import type { StoryBody } from "../types";

export function StoryText({ body }: { body: StoryBody }) {
  const paragraphs = body.text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
  return (
    <div className="flex flex-col gap-4">
      {paragraphs.map((p, i) => (
        <Prose key={i}>{p}</Prose>
      ))}
    </div>
  );
}
