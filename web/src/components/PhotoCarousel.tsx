import { useState, type UIEvent } from "react";
import { Picture, PhotoCredit, PhotoDots } from "./Picture";
import { MonoLabel } from "./Article";
import { cx } from "../cx";
import type { StoryPhoto } from "../types";

interface PhotoCarouselProps {
  photos: [StoryPhoto, ...StoryPhoto[]];
  height?: number;
  visibleHeight?: number;
  className?: string;
}

export function PhotoCarousel({ photos, height = 260, visibleHeight = height, className }: PhotoCarouselProps) {
  const [index, setIndex] = useState(0);
  const current = photos[Math.min(index, photos.length - 1)];

  const onScroll = (e: UIEvent<HTMLDivElement>) => {
    const { scrollLeft, clientWidth } = e.currentTarget;
    if (clientWidth > 0) setIndex(Math.round(scrollLeft / clientWidth));
  };

  return (
    <figure className={cx("m-0 flex flex-col", className)}>
      <div
        className="relative overflow-hidden rounded-[20px] transition-[height] duration-700 ease-smooth motion-reduce:transition-none"
        style={{ height: visibleHeight }}
      >
        <div
          onScroll={onScroll}
          className="flex snap-x snap-mandatory overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          style={{ height }}
        >
          {photos.map((photo, i) => (
            <div key={`${photo.src ?? photo.alt}-${i}`} className="w-full shrink-0 snap-center">
              <Picture
                variant="photo"
                height={height}
                radius={0}
                year={photo.year}
                src={photo.src}
                alt={photo.alt}
                credit={false}
              />
            </div>
          ))}
        </div>
        {photos.length > 1 && <PhotoDots count={photos.length} index={index} className="bottom-3" />}
      </div>
      <figcaption
        aria-live="polite"
        className={cx(
          "flex flex-col gap-0.5 overflow-hidden transition-[max-height,opacity,margin] duration-700 ease-smooth motion-reduce:transition-none",
          visibleHeight > 0 ? "mt-2 max-h-24 opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <span className="text-[15px] leading-[1.35]">
          <MonoLabel tone="bus">{current.year}</MonoLabel> · {current.caption}
        </span>
        <PhotoCredit text={current.credit} overlay={false} />
      </figcaption>
    </figure>
  );
}
