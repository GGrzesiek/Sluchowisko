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

const START = 14;
const END_PAD = 38;

function stopX(index: number, count: number, offset = 0): string {
  const fraction = count > 1 ? index / (count - 1) : 0;
  return `calc(${START + offset}px + (100% - ${START + END_PAD}px) * ${fraction})`;
}

export function RouteStrip({
  stops: allStops,
  before = 1,
  after = 2,
  height = 200,
  axisY = 160,
  showLegend = false,
  className,
}: RouteStripProps) {
  const stops = windowStops(allStops, before, after);
  const currentIndex = stops.findIndex((s) => s.state === "current");
  const splitX = currentIndex >= 0 ? stopX(currentIndex, stops.length) : "0px";
  return (
    <div role="img" aria-label={describeStops(stops)} className={cx("relative", className)} style={{ height }}>
      <span className="absolute left-0 h-[3px] bg-road" style={{ top: axisY - 1.5, width: splitX }} />
      <span className="absolute right-2.5 h-[3px] bg-ink" style={{ top: axisY - 1.5, left: splitX }} />
      <span
        className="absolute right-0 h-0 w-0 border-y-[6.5px] border-l-[11px] border-y-transparent border-l-ink"
        style={{ top: axisY - 6.5 }}
      />
      {stops.map((s, i) => {
        const n = stops.length;
        const now = s.state === "current";
        const passed = s.state === "passed";
        const size = now ? 14 : passed ? 10 : 12;
        return (
          <div key={`${s.name}-${i}`}>
            <span
              className={cx(
                "absolute origin-left -rotate-50 whitespace-nowrap",
                now
                  ? "text-base font-extrabold text-bus"
                  : passed
                    ? "text-[13px] font-medium text-umber"
                    : "text-[13px] font-medium text-ink",
              )}
              style={{ left: stopX(i, n, 4), top: axisY - 26 }}
            >
              {s.name}
            </span>
            {now && (
              <>
                <span
                  className="animate-ping-soft absolute box-border border-2 border-bus"
                  style={{ left: stopX(i, n, -size / 2), top: axisY - size / 2, width: size, height: size }}
                />
                <span
                  className="animate-ping-soft absolute box-border border-2 border-bus [animation-delay:0.9s]"
                  style={{ left: stopX(i, n, -size / 2), top: axisY - size / 2, width: size, height: size }}
                />
              </>
            )}
            <span
              className={cx(
                "absolute box-border",
                now && "animate-beat bg-bus",
                passed && "bg-road",
                !now && !passed && "border-[2.5px] border-ink bg-paper",
              )}
              style={{ left: stopX(i, n, -size / 2), top: axisY - size / 2, width: size, height: size }}
            />
            {s.hasStory && (
              <span
                className={cx("absolute", now ? "text-bus" : "text-umber")}
                style={{ left: stopX(i, n, -7), top: axisY + 20 }}
              >
                <UiIcon name="headphones" size={14} strokeWidth={2.4} />
              </span>
            )}
            {s.etaMinutes != null && (
              <span
                className="absolute whitespace-nowrap font-mono text-[11px] font-semibold tracking-[0.04em] text-ink"
                style={{ left: stopX(i, n, -14), top: axisY + 20 }}
              >
                {s.etaMinutes} MIN
              </span>
            )}
          </div>
        );
      })}
      {showLegend && (
        <div className="absolute bottom-0 left-0 flex items-center gap-2 text-sm font-semibold text-umber">
          <UiIcon name="headphones" size={27} strokeWidth={2.4} />
          <span className="text-base">Załóż słuchawki</span>
        </div>
      )}
    </div>
  );
}
