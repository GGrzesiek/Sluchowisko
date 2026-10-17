import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../cx";
import { PauseGlyph, PlayGlyph } from "./Icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "outline" | "ghost";
  size?: "lg" | "md";
  icon?: ReactNode;
};

export function Button({
  variant = "primary",
  size = "lg",
  icon,
  className,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        "flex items-center justify-center font-extrabold transition-transform active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100",
        variant === "primary" &&
          (size === "lg"
            ? "h-16 gap-3 rounded-[20px] bg-bus text-xl text-cream"
            : "h-[58px] gap-2.5 rounded-[18px] bg-bus text-lg text-cream"),
        variant === "secondary" &&
          "h-[52px] gap-2.5 rounded-2xl border-2 border-charcoal bg-transparent px-4 text-[17px] text-charcoal",
        variant === "outline" &&
          "h-16 gap-3 rounded-[20px] border-[1.5px] border-charcoal bg-transparent px-4 text-xl text-charcoal",
        variant === "ghost" &&
          "h-12 rounded-[14px] border-[1.5px] border-road bg-transparent px-4 text-[15px] font-bold text-charcoal",
        className,
      )}
      {...rest}
    >
      {icon}
      {typeof children === "string" ? <span>{children}</span> : children}
    </button>
  );
}

interface PlayButtonProps {
  playing: boolean;
  onToggle?: () => void;
}

export function PlayButton({ playing, onToggle }: PlayButtonProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={playing ? "Pauza" : "Odtwórz"}
      className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-bus text-cream"
    >
      {playing ? <PauseGlyph /> : <PlayGlyph />}
    </button>
  );
}

export function IconButton({ label, children, onClick }: { label: string; children: ReactNode; onClick?: () => void }) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex h-11 w-11 items-center justify-center rounded-full bg-puff text-charcoal"
    >
      {children}
    </button>
  );
}
