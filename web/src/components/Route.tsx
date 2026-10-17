import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { UiIcon } from "./Icon";
import { cx } from "../cx";
import type { RouteStop } from "../types";

interface RouteStripProps {
  stops: RouteStop[];
  height?: number;
  axisY?: number;
  before?: number;
  after?: number;
  showLegend?: boolean;
  className?: string;
}

export function pluralMinutes(n: number): string {
  if (n === 1) return "1 minutę";
  const lastTwo = n % 100;
  const last = n % 10;
  return last >= 2 && last <= 4 && !(lastTwo >= 12 && lastTwo <= 14) ? `${n} minuty` : `${n} minut`;
}

export function describeStops(stops: RouteStop[]): string {
  const names = (state: RouteStop["state"]) => stops.filter((s) => s.state === state);
  const parts: string[] = [];
  const passed = names("passed");
  if (passed.length) parts.push(`poprzednie ${passed.map((s) => s.name).join(", ")}`);
  const current = names("current");
  if (current.length) parts.push(`teraz ${current.map((s) => s.name).join(", ")}`);
  const upcoming = stops.filter((s) => s.state === "next" || s.state === "upcoming");
  if (upcoming.length) {
    const list = upcoming
      .map((s) => (s.etaMinutes != null ? `${s.name} za ${pluralMinutes(s.etaMinutes)}` : s.name))
      .join(", ");
    parts.push(`następne ${list}`);
  }
  return `Przystanki: ${parts.join("; ")}`;
}

export function windowStops(stops: RouteStop[], before: number, after: number): RouteStop[] {
  const current = stops.findIndex((s) => s.state === "current");
  if (current < 0) return stops.slice(0, before + after + 1);
  return stops.slice(Math.max(0, current - before), current + after + 1);
}

const FADE_MASK = "[mask-image:linear-gradient(to_right,black_calc(100%-28px),transparent)]";
const START = 14;
const END_PAD = 38;

function stopX(index: number, count: number, offset = 0): string {
  const fraction = count > 1 ? index / (count - 1) : 0;
  return `calc(${START + offset}px + (100% - ${START + END_PAD}px) * ${fraction})`;
}

const MOVE =
  "transition-[left,top,bottom,width,height,opacity,color,background-color,border-color] duration-700 ease-smooth motion-reduce:transition-none";

function stopKeys(stops: RouteStop[]): string[] {
  const seen = new Map<string, number>();
  return stops.map((s) => {
    const n = (seen.get(s.name) ?? 0) + 1;
    seen.set(s.name, n);
    return `${s.name}#${n}`;
  });
}

interface StopLabelProps {
  name: string;
  maxWidth: number;
  className?: string;
  style: CSSProperties;
}

function StopLabel({ name, maxWidth, className, style }: StopLabelProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const [clipped, setClipped] = useState(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (el) setClipped(el.scrollWidth > el.clientWidth + 1);
  }, [name, maxWidth]);

  return (
    <span
      ref={ref}
      title={clipped ? name : undefined}
      className={cx(
        "absolute origin-left -rotate-50 overflow-hidden whitespace-nowrap",
        MOVE,
        clipped && FADE_MASK,
        className,
      )}
      style={{ ...style, maxWidth }}
    >
      {name}
    </span>
  );
}

export function RouteStrip({
  stops: allStops,
  before = 1,
  after = 2,
  height = 200,
  axisY = 160,
  showLegend,
  className,
}: RouteStripProps) {
  const stops = windowStops(allStops, before, after);
  const slots = before + after + 1;
  const keys = stopKeys(allStops);
  const currentIdx = allStops.findIndex((s) => s.state === "current");
  const reference = currentIdx >= 0 ? currentIdx : before;
  const [initial] = useState(() => new Map(allStops.map((s, i) => [keys[i], s.etaMinutes])));
  const splitX = stopX(before, slots);
  return (
    <div
      role="img"
      aria-label={describeStops(stops)}
      className={cx("relative transition-[height] duration-700 ease-smooth motion-reduce:transition-none", className)}
      style={{ height }}
    >
      <span className={cx("absolute left-0 h-[3px] bg-road", MOVE)} style={{ top: axisY - 1.5, width: splitX }} />
      <span className={cx("absolute right-2.5 h-[3px] bg-ink", MOVE)} style={{ top: axisY - 1.5, left: splitX }} />
      <span
        className={cx(
          "absolute right-0 h-0 w-0 border-y-[6.5px] border-l-[11px] border-y-transparent border-l-ink",
          MOVE,
        )}
        style={{ top: axisY - 6.5 }}
      />
      {allStops.map((s, i) => {
        const slot = i - reference + before;
        if (slot < -1 || slot > slots) return null;
        const shown = slot >= 0 && slot < slots;
        const n = slots;
        const k = keys[i];
        const now = s.state === "current";
        const passed = s.state === "passed";
        const size = now ? 14 : passed ? 10 : 12;
        return (
          <div
            key={k}
            aria-hidden={!shown}
            className={cx(
              "transition-opacity duration-700 ease-smooth motion-reduce:transition-none",
              !shown && "pointer-events-none opacity-0",
            )}
          >
            <StopLabel
              name={s.name}
              maxWidth={now ? 176 : 140}
              className={cx(
                now
                  ? "text-base font-extrabold text-bus"
                  : passed
                    ? "text-[13px] font-medium text-umber"
                    : "text-[13px] font-medium text-ink",
              )}
              style={{ left: stopX(slot, n, 4), top: axisY - 26 }}
            />
            {now && (
              <>
                <span
                  className={cx("animate-ping-soft absolute box-border border-2 border-bus", MOVE)}
                  style={{ left: stopX(slot, n, -size / 2), top: axisY - size / 2, width: size, height: size }}
                />
                <span
                  className={cx(
                    "animate-ping-soft absolute box-border border-2 border-bus [animation-delay:0.9s]",
                    MOVE,
                  )}
                  style={{ left: stopX(slot, n, -size / 2), top: axisY - size / 2, width: size, height: size }}
                />
              </>
            )}
            <span
              className={cx(
                "absolute box-border",
                MOVE,
                now && "animate-beat bg-bus",
                passed && "bg-road",
                !now && !passed && "border-[2.5px] border-ink bg-paper",
              )}
              style={{ left: stopX(slot, n, -size / 2), top: axisY - size / 2, width: size, height: size }}
            />
            {s.hasStory && (
              <span
                className={cx("absolute", MOVE, now ? "text-bus" : "text-umber")}
                style={{ left: stopX(slot, n, -7), top: axisY + 20 }}
              >
                <UiIcon name="headphones" size={14} strokeWidth={2.4} />
              </span>
            )}
            {s.etaMinutes != null && (
              <span
                key={s.etaMinutes}
                className={cx(
                  "absolute whitespace-nowrap font-mono text-[11px] font-semibold tracking-[0.04em] text-ink",
                  !(initial.has(k) && initial.get(k) === s.etaMinutes) && "animate-fade-in",
                  MOVE,
                )}
                style={{ left: stopX(slot, n, -14), top: axisY + 20 }}
              >
                {s.etaMinutes} MIN
              </span>
            )}
          </div>
        );
      })}
      {showLegend !== undefined && (
        <div
          aria-hidden={!showLegend}
          className={cx(
            "absolute bottom-0 left-0 flex items-center gap-2 text-sm font-semibold text-umber transition-opacity duration-500 ease-smooth motion-reduce:transition-none",
            showLegend ? "opacity-100" : "opacity-0",
          )}
        >
          <UiIcon name="headphones" size={27} strokeWidth={2.4} />
          <span className="text-base">Załóż słuchawki</span>
        </div>
      )}
    </div>
  );
}
