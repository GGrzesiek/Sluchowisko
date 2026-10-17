import { UiIcon } from "./Icon";
import { cx } from "../cx";
import type { RouteStop } from "../types";

interface RouteStripProps {
  stops: RouteStop[];
  height?: number;
  axisY?: number;
  showLegend?: boolean;
  className?: string;
}

const STEP = 58;
const START = 14;

export function RouteStrip({ stops, height = 200, axisY = 160, showLegend = false, className }: RouteStripProps) {
  const currentIndex = stops.findIndex((s) => s.state === "current");
  const splitX = currentIndex >= 0 ? START + currentIndex * STEP : 0;
  const summary = stops.map((s) => `${s.state === "current" ? "teraz" : s.state}: ${s.name}`).join(", ");
  return (
    <div role="img" aria-label={`Przystanki: ${summary}`} className={cx("relative", className)} style={{ height }}>
      <span className="absolute left-0 h-[3px] bg-road" style={{ top: axisY - 1.5, width: splitX }} />
      <span className="absolute right-2.5 h-[3px] bg-ink" style={{ top: axisY - 1.5, left: splitX }} />
      <span
        className="absolute right-0 h-0 w-0 border-y-[6.5px] border-l-[11px] border-y-transparent border-l-ink"
        style={{ top: axisY - 6.5 }}
      />
      {stops.map((s, i) => {
        const x = START + i * STEP;
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
              style={{ left: x + 4, top: axisY - 26 }}
            >
              {s.name}
            </span>
            {now && (
              <>
                <span
                  className="animate-ping-soft absolute box-border border-2 border-bus"
                  style={{ left: x - size / 2, top: axisY - size / 2, width: size, height: size }}
                />
                <span
                  className="animate-ping-soft absolute box-border border-2 border-bus [animation-delay:0.9s]"
                  style={{ left: x - size / 2, top: axisY - size / 2, width: size, height: size }}
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
              style={{ left: x - size / 2, top: axisY - size / 2, width: size, height: size }}
            />
            {s.hasStory && (
              <span
                className={cx("absolute", now ? "text-bus" : "text-umber")}
                style={{ left: x - 7, top: axisY + 20 }}
              >
                <UiIcon name="headphones" size={14} strokeWidth={2.4} />
              </span>
            )}
            {s.etaLabel && (
              <span
                className="absolute whitespace-nowrap font-mono text-[11px] font-semibold tracking-[0.04em] text-ink"
                style={{ left: x - 14, top: axisY + 20 }}
              >
                {s.etaLabel}
              </span>
            )}
          </div>
        );
      })}
      {showLegend && (
        <div className="absolute bottom-0 left-0 flex items-center gap-1.5 text-xs text-umber">
          <UiIcon name="headphones" size={13} strokeWidth={2.4} />
          <span>historia przy przystanku</span>
        </div>
      )}
    </div>
  );
}
