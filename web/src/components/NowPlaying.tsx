import { PlayButton } from "./Button";
import { ProgressBar } from "./Progress";
import { cx } from "../cx";

interface NowPlayingBarProps {
  title: string;
  playing: boolean;
  elapsedLabel: string;
  totalLabel: string;
  progress: number;
  onToggle?: () => void;
  className?: string;
}

export function NowPlayingBar({
  title,
  playing,
  elapsedLabel,
  totalLabel,
  progress,
  onToggle,
  className,
}: NowPlayingBarProps) {
  return (
    <div className={cx("flex h-[86px] items-center gap-3 rounded-[20px] bg-sand py-0 pl-4 pr-2", className)}>
      <div className="flex min-w-0 grow flex-col gap-1">
        <span className="truncate font-mono text-[10px] font-semibold tracking-[0.08em] text-umber">
          TERAZ · {elapsedLabel} / {totalLabel}
        </span>
        <span className="truncate text-[17px] font-extrabold leading-[1.1]">{title}</span>
        <ProgressBar value={progress} surface="sand" />
      </div>
      <PlayButton playing={playing} onToggle={onToggle} />
    </div>
  );
}
