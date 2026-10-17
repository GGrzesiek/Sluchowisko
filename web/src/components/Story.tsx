import { Grain } from "./Grain";
import { Picture } from "./Picture";
import { ProgressBar } from "./Progress";
import { cx } from "../cx";
import type { PictureVariant, StoryCardState, StoryIconKind } from "../types";

export interface StoryThumb {
  variant: PictureVariant;
  year?: string;
  icon?: StoryIconKind;
  src?: string;
}

interface StoryCardProps {
  state: StoryCardState;
  title: string;
  thumb: StoryThumb;
  etaLabel?: string;
  elapsedLabel?: string;
  progress?: number;
  onClick?: () => void;
}

export function Thumb({ thumb, size, dim }: { thumb: StoryThumb; size: number; dim?: boolean }) {
  return (
    <div
      className={cx("relative shrink-0 overflow-hidden rounded-xl", dim && "opacity-60")}
      style={{ width: size, height: size }}
    >
      <Picture {...thumb} height={size} radius={12} credit={false} photoCount={1} />
    </div>
  );
}

export function StoryCard({ state, title, thumb, etaLabel, elapsedLabel, progress = 0, onClick }: StoryCardProps) {
  const Tag = onClick ? "button" : "div";
  const base = "relative flex min-h-24 w-full items-center gap-3 overflow-hidden rounded-[20px] p-3.5 text-left";
  if (state === "playing") {
    return (
      <Tag onClick={onClick} className={cx(base, "bg-charcoal text-cream")}>
        <Thumb thumb={thumb} size={60} />
        <div className="flex min-w-0 grow flex-col gap-1.5">
          <span className="text-[11px] font-extrabold uppercase tracking-[0.06em] text-mustard">
            Teraz gra{elapsedLabel ? ` · ${elapsedLabel}` : ""}
          </span>
          <span className="font-serif text-lg font-semibold leading-[1.12]">{title}</span>
          <ProgressBar value={progress} />
        </div>
      </Tag>
    );
  }
  if (state === "skipped") {
    return (
      <Tag onClick={onClick} className={cx(base, "border-[1.5px] border-dashed border-road")}>
        <Thumb thumb={thumb} size={60} dim />
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-[11px] font-extrabold uppercase tracking-[0.06em] text-umber">
            Pominięta · dotknij, by posłuchać
          </span>
          <span className="font-serif text-lg font-semibold leading-[1.12] text-umber">{title}</span>
        </div>
      </Tag>
    );
  }
  return (
    <Tag onClick={onClick} className={cx(base, "bg-sand text-hair")}>
      <Grain opacity={0.35} />
      <div className="relative">
        <Thumb thumb={thumb} size={60} />
      </div>
      <div className="relative flex min-w-0 flex-col gap-1">
        <span className="text-[11px] font-extrabold uppercase tracking-[0.06em]">
          Następna{etaLabel ? ` ${etaLabel}` : ""}
        </span>
        <span className="font-serif text-lg font-semibold leading-[1.12]">{title}</span>
      </div>
    </Tag>
  );
}
