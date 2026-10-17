import { UiIcon } from "./Icon";
import { cx } from "../cx";
import type { LineKind } from "../types";

interface LineBadgeProps {
  line: string;
  kind?: LineKind;
  size?: "lg" | "md" | "sm";
  label?: string;
}

const KIND_STYLE: Record<LineKind, string> = {
  bus: "bg-bus text-cream",
  tram: "bg-mustard text-charcoal",
  night: "bg-charcoal text-mustard",
  plain: "border-2 border-dashed border-umber text-umber",
};

const KIND_LABEL: Record<LineKind, string> = {
  bus: "Autobus",
  tram: "Tramwaj",
  night: "Nocny",
  plain: "Bez historii",
};

const SIZE_STYLE = {
  lg: "h-16 min-w-24 gap-1.5 rounded-[14px] px-3.5 text-[52px]",
  md: "h-14 min-w-[84px] gap-1.5 rounded-xl px-3 text-[44px]",
  sm: "h-9 min-w-14 rounded-[9px] px-2 text-[26px]",
} as const;

export function LineChip({ line, tone = "cream" }: { line: string; tone?: "cream" | "bus" }) {
  return (
    <span
      className={cx(
        "font-condensed inline-block rounded-lg px-2 font-black",
        tone === "bus" ? "bg-bus text-cream" : "bg-cream text-bus",
      )}
    >
      {line}
    </span>
  );
}

export function LineBadge({ line, kind = "bus", size = "lg", label }: LineBadgeProps) {
  const large = size !== "sm";
  return (
    <span
      role="img"
      aria-label={label ?? `${KIND_LABEL[kind]} ${line}`}
      className={cx(
        "font-condensed inline-flex items-center justify-center font-black",
        SIZE_STYLE[size],
        KIND_STYLE[kind],
      )}
    >
      {kind === "night" && <UiIcon name="moon" size={large ? 20 : 12} strokeWidth={2.4} />}
      <span aria-hidden="true">{line}</span>
    </span>
  );
}

export function VehicleTag({ number }: { number: string }) {
  return (
    <span
      aria-label={`Pojazd ${number}`}
      className="font-condensed inline-flex h-10 items-center justify-center rounded-lg bg-charcoal px-3 text-[28px] font-black tracking-[0.04em] text-cream"
    >
      {number}
    </span>
  );
}
