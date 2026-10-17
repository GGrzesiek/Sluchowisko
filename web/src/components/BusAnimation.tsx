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
  { left: 283, top: 105, size: 20, delay: "0s" },
  { left: 284, top: 107, size: 16, delay: "0.4s" },
  { left: 282, top: 104, size: 22, delay: "0.8s" },
  { left: 284, top: 106, size: 18, delay: "1.2s" },
];

export function BusAnimation({ className }: { className?: string }) {
  return (
    <div
      role="img"
      aria-label="Animacja: ogórek jedzie przez ekran"
      className={cx("relative h-[230px] overflow-hidden", className)}
    >
      <div className="absolute inset-x-0 bottom-10 h-[3px] bg-ink" />
      <div className="absolute inset-x-0 bottom-[22px] h-1 overflow-hidden">
        <div className="-ml-12 h-1 w-[calc(100%+48px)] animate-road bg-[repeating-linear-gradient(90deg,var(--color-road)_0_24px,transparent_24px_48px)] motion-reduce:animate-none" />
      </div>
      <div className="absolute inset-x-0 bottom-9 h-[134px] animate-drive motion-reduce:translate-x-[calc(50%-150px)] motion-reduce:animate-none">
        <div className="absolute bottom-0 left-0 h-[134px] w-[300px]">
          <div className="absolute inset-x-5 -bottom-1 h-2.5 rounded-[50%] bg-ground" />
          {PUFFS.map((p) => (
            <div
              key={p.delay}
              className="absolute animate-puff rounded-full border border-ink/30 bg-puff opacity-0 motion-reduce:hidden"
              style={{ left: p.left, top: p.top, width: p.size, height: p.size, animationDelay: p.delay }}
            />
          ))}
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
  );
}
