import { useEffect, useState } from "react";
import { PLACEHOLDER_RIDE, PLACEHOLDER_STORY } from "./data/placeholderRide";
import { JourneyScreen } from "./screens/JourneyScreen";
import type { StoryContent } from "./types";

export function previewIdFromHash(hash: string): string | null {
  const match = /^#\/preview\/(\d{1,10})$/.exec(hash);
  return match ? match[1] : null;
}

export function StoryPreview({ id }: { id: string }) {
  const [story, setStory] = useState<StoryContent | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}preview/${id}.json`)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(String(response.status)))))
      .then((content: StoryContent) => !cancelled && setStory(content))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (failed) return <p className="p-6">Brak podglądu historii {id}.</p>;
  if (!story) return null;
  return <JourneyScreen ride={PLACEHOLDER_RIDE} story={{ ...story, audio: story.audio ?? PLACEHOLDER_STORY.audio }} />;
}
