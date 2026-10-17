import type { CSSProperties } from "react";
import ogorek from "../assets/ogorek.png";
import { cx } from "../cx";

const WHEELS = [
  { x: 310, y: 373, sx: 1, sy: 1.07 },
  { x: 817, y: 357, sx: 0.87, sy: 0.96 },
];

const BOLTS = [0, 60, 120, 180, 240, 300].map((deg) => {
  const rad = (deg * Math.PI) / 180;
  return { cx: 17 * Math.sin(rad), cy: -17 * Math.cos(rad) };
});

const PUFFS = [
  {
    left: 283,
    top: 105,
    size: 20,
    dx: 96,
    dy: -58,
    grow: 2.4,
    radius: "58% 42% 63% 37% / 48% 57% 43% 52%",
    delay: "0s",
  },
  {
    left: 284,
    top: 107,
    size: 14,
    dx: 70,
    dy: -30,
    grow: 1.9,
    radius: "44% 56% 38% 62% / 60% 42% 58% 40%",
    delay: "0.3s",
  },
  {
    left: 282,
    top: 104,
    size: 24,
    dx: 110,
    dy: -80,
    grow: 2.8,
    radius: "65% 35% 52% 48% / 40% 62% 38% 60%",
    delay: "0.6s",
  },
  {
    left: 284,
    top: 106,
    size: 16,
    dx: 84,
    dy: -18,
    grow: 2,
    radius: "50% 50% 66% 34% / 57% 38% 62% 43%",
    delay: "0.9s",
  },
  {
    left: 283,
    top: 105,
    size: 18,
    dx: 62,
    dy: -70,
    grow: 2.2,
    radius: "37% 63% 47% 53% / 52% 61% 39% 48%",
    delay: "1.2s",
  },
  {
    left: 284,
    top: 107,
    size: 12,
    dx: 100,
    dy: -44,
    grow: 1.7,
    radius: "61% 39% 41% 59% / 45% 55% 45% 55%",
    delay: "1.5s",
  },
  {
    left: 282,
    top: 105,
    size: 22,
    dx: 78,
    dy: -62,
    grow: 2.6,
    radius: "47% 53% 60% 40% / 63% 44% 56% 37%",
    delay: "1.8s",
  },
];

const LOOP_S = 5.4;
const PUFF_EVERY_S = 0.3;
const BUS_WIDTH = 300;
const BUS_TOP = 71;

const TRAIL = Array.from({ length: Math.round(LOOP_S / PUFF_EVERY_S) }, (_, i) => {
  const base = PUFFS[i % PUFFS.length];
  const progress = (i * PUFF_EVERY_S) / LOOP_S;
  return {
    ...base,
    key: i,
    left: `calc(${(1 - progress) * 100}% + ${base.left - BUS_WIDTH * progress}px)`,
    top: BUS_TOP + base.top,
    delay: `${i * PUFF_EVERY_S}s`,
  };
});

export function BusAnimation({ className }: { className?: string }) {
  return (
    <div
      role="img"
      aria-label="Animacja: ogórek jedzie przez ekran"
      className={cx("relative h-[230px] overflow-hidden", className)}
    >
      <div className="absolute inset-x-0 bottom-10 h-[3px] bg-ink" />
      <div className="absolute inset-x-0 bottom-[8px] h-1 overflow-hidden">
        <div className="-ml-12 h-1 w-[calc(100%+48px)] animate-road bg-[repeating-linear-gradient(90deg,var(--color-road)_0_24px,transparent_24px_48px)] motion-reduce:animate-none" />
      </div>
      {TRAIL.map((p) => (
        <div
          key={p.key}
          aria-hidden="true"
          className="absolute animate-puff opacity-0 motion-reduce:hidden"
          style={
            {
              left: p.left,
              top: p.top,
              width: p.size,
              height: p.size,
              borderRadius: p.radius,
              animationDelay: p.delay,
              "--dx": `${p.dx}px`,
              "--dy": `${p.dy}px`,
              "--grow": p.grow,
            } as CSSProperties
          }
        />
      ))}
      <div className="absolute inset-x-0 bottom-[20px] h-[134px] animate-drive motion-reduce:translate-x-[calc(50%-150px)] motion-reduce:animate-none">
        <div className="absolute bottom-0 left-0 h-[134px] w-[300px]">
          <div className="absolute inset-x-5 -bottom-px z-0 h-2.5 rounded-[50%] bg-ink/15" />
          <div className="absolute inset-0 z-10 origin-bottom rotate-2">
            <div className="absolute inset-0 origin-bottom animate-rattle motion-reduce:animate-none">
              <img src={ogorek} alt="" className="absolute inset-0 h-[134px] w-[300px]" />
              <svg width="300" height="134" viewBox="0 0 1007 450" aria-hidden="true" className="absolute inset-0">
                {WHEELS.map((w) => (
                  <g key={w.x} transform={`translate(${w.x} ${w.y}) scale(${w.sx} ${w.sy})`}>
                    <g className="origin-center animate-wheel [transform-box:fill-box] motion-reduce:animate-none">
                      <circle r="37" fill="var(--color-chrome)" stroke="var(--color-tyre)" strokeWidth="4" />
                      <circle r="27" fill="none" stroke="#8e8c87" strokeWidth="3" />
                      {BOLTS.map((b) => (
                        <circle key={`${b.cx}-${b.cy}`} cx={b.cx} cy={b.cy} r="4.5" fill="var(--color-glass-top)" />
                      ))}
                      <circle r="9" fill="var(--color-ground)" stroke="var(--color-tyre)" strokeWidth="3" />
                    </g>
                  </g>
                ))}
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
