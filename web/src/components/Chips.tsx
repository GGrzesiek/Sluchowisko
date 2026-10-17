import { StoryIcon, UiIcon } from "./Icon";
import { cx } from "../cx";
import type { LookDirection, StoryIconKind } from "../types";

interface StoryMarkerProps {
  title: string;
  distanceLabel: string;
  icon: StoryIconKind;
}

export function StoryMarker({ title, distanceLabel, icon }: StoryMarkerProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex h-[30px] w-[30px] items-center justify-center rounded-full bg-mustard text-charcoal">
        <StoryIcon kind={icon} size={16} strokeWidth={2.2} />
      </span>
      <span className="flex items-baseline gap-2 rounded-xl bg-sand px-3 py-1.5">
        <span className="font-serif text-[17px] font-semibold">{title}</span>
        <span className="text-[13px] font-semibold text-umber">· {distanceLabel}</span>
      </span>
    </div>
  );
}

interface LookChipProps {
  direction: LookDirection;
  label: string;
  active?: boolean;
}

export function LookChip({ direction, label, active = true }: LookChipProps) {
  if (direction === "around") {
    return (
      <span
        className={cx(
          "inline-flex h-10 items-center rounded-full px-3.5 text-[15px]",
          active ? "bg-mustard font-extrabold text-charcoal" : "border-[1.5px] border-road font-bold",
        )}
      >
        {label}
      </span>
    );
  }
  const left = direction === "left";
  return (
    <span
      className={cx(
        "inline-flex h-10 items-center gap-2 rounded-full bg-mustard text-[15px] font-extrabold text-charcoal",
        left ? "pl-2.5 pr-3.5" : "pl-3.5 pr-2.5",
      )}
    >
      {left && <UiIcon name="arrowLeft" size={20} strokeWidth={2.6} />}
      <span>{label}</span>
      {!left && <UiIcon name="arrowRight" size={20} strokeWidth={2.6} />}
    </span>
  );
}
