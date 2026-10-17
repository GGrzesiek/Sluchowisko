import { cx } from "../cx";

interface ProgressBarProps {
  value: number;
  surface?: "dark" | "sand";
}

export function ProgressBar({ value, surface = "dark" }: ProgressBarProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const dark = surface === "dark";
  return (
    <div
      role="progressbar"
      aria-label="Postęp historii"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={cx("relative rounded-full", dark ? "h-1 bg-umber" : "h-[3px] bg-ground")}
    >
      <div
        className={cx("absolute inset-y-0 left-0 rounded-full", dark ? "bg-cream" : "bg-charcoal")}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
