import { useEffect, useState } from "react";
import {
  NowPlayingBar,
  PhotoCarousel,
  RouteStrip,
  SourceList,
  StoryHeading,
  StoryText,
  UiIcon,
  VehicleHeader,
} from "../components";
import { cx } from "../cx";
import { clock, useNarration } from "../Narration";
import type { RideInfo, StoryContent } from "../types";

interface JourneyScreenProps {
  ride: RideInfo;
  story: StoryContent;
  onClose?: () => void;
}

const PHOTO_HEIGHT = 260;
const INTRO_STRIP = { height: 300, axisY: 210 };
const HINT_FADE_DISTANCE = 80;
const SETTLED_STRIP = { height: 214, axisY: 168 };

export function JourneyScreen({ ride, story, onClose }: JourneyScreenProps) {
  const [settled, setSettled] = useState(false);
  const narration = useNarration();
  const ours = Boolean(story.audio) && narration.src === story.audio;
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => setSettled(true));
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, []);

  useEffect(() => {
    let frame = 0;
    const update = () => setScrollProgress(Math.min(1, Math.max(0, window.scrollY / HINT_FADE_DISTANCE)));
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  const strip = settled ? SETTLED_STRIP : INTRO_STRIP;

  return (
    <main className="mx-auto w-full max-w-[430px] bg-paper px-6 pb-4">
      <section className="flex min-h-dvh flex-col pb-[118px] pt-5">
        <VehicleHeader vehicle={ride.vehicle} destination={ride.destination} onClose={onClose} />
        <PhotoCarousel
          photos={story.photos}
          height={PHOTO_HEIGHT}
          visibleHeight={settled ? PHOTO_HEIGHT : 0}
          className={cx(
            "transition-[margin] duration-700 ease-smooth motion-reduce:transition-none",
            settled ? "mt-3" : "mt-[116px]",
          )}
        />
        <RouteStrip
          stops={ride.stops}
          height={strip.height}
          axisY={strip.axisY}
          showLegend={!settled}
          className="mt-2"
        />
        <div
          aria-hidden="true"
          className={cx(
            "pointer-events-none fixed inset-x-0 bottom-[118px] z-10 mx-auto max-w-[430px] transition-opacity duration-700 ease-smooth motion-reduce:transition-none",
            settled ? "opacity-100" : "opacity-0",
          )}
        >
          <div
            className="flex flex-col items-center gap-1 text-umber will-change-transform"
            style={{
              opacity: 1 - scrollProgress,
              transform: `translateY(${-scrollProgress * 20}px) scale(${1 - scrollProgress * 0.06})`,
            }}
          >
            <span className="animate-nudge flex">
              <UiIcon name="chevron" size={22} className="-rotate-90" />
            </span>
            <span className="text-sm font-semibold">Przesuń w górę, by dowiedzieć się więcej</span>
          </div>
        </div>
      </section>
      <section className="flex flex-col gap-5 pb-32 pt-4">
        <StoryHeading title={story.title} />
        <StoryText body={story.body} />
        <SourceList sources={story.sources} />
      </section>
      {story.audio && (
        <NowPlayingBar
          title={story.title}
          playing={ours && narration.playing}
          elapsedLabel={clock(ours ? narration.elapsed : 0)}
          totalLabel={ours ? clock(narration.duration) : "--:--"}
          progress={ours && narration.duration > 0 ? narration.elapsed / narration.duration : 0}
          onToggle={() => narration.toggle(story)}
          className="animate-fade-in sticky bottom-4 shadow-lg"
        />
      )}
    </main>
  );
}
