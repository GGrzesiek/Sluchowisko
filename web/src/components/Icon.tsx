import type { StoryIconKind } from "../types";

export const STORY_ICON_PATHS: Record<StoryIconKind, string> = {
  patron: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6",
  oldname: "M4 6h13l3 3-3 3H4z M9 12v9 M7 21h4",
  bazaar: "M3 9l2-5h14l2 5 M3 9h18 M5 12v8h14v-8 M10 20v-4h4v4",
  cinema: "M4 5h16v14H4z M8 5v14 M16 5v14 M4 9h4 M4 15h4 M16 9h4 M16 15h4",
  building: "M3 21h18 M4 10l8-6 8 6 M6 10v9 M10 10v9 M14 10v9 M18 10v9",
  river:
    "M12 3c-3 0-5 2.5-5 5.5S9 14 12 14s5-2.5 5-5.5S15 3 12 3z M12 14v4 M3 20c2 0 2-1 4.5-1s2.5 1 4.5 1 2-1 4.5-1 2.5 1 4.5 1",
  event:
    "M4 6h16v14H4z M4 10h16 M8 3v5 M16 3v5 M12 12.5l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z",
};

export const STORY_ICON_LABELS: Record<StoryIconKind, string> = {
  patron: "Patron ulicy",
  oldname: "Dawna nazwa",
  bazaar: "Bazar / targ",
  cinema: "Kino / teatr",
  building: "Budynek",
  river: "Rzeka / park",
  event: "Wydarzenie",
};

const UI_PATHS = {
  arrowLeft: "M19 12H5 M11 6l-6 6 6 6",
  arrowRight: "M5 12h14 M13 6l6 6-6 6",
  headphones: "M4 15v-3a8 8 0 0 1 16 0v3 M4 15h3v5H4z M17 15h3v5h-3z",
  close: "M6 6l12 12 M18 6L6 18",
  moon: "M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z",
  chevron: "M9 6l6 6-6 6",
  external: "M14 4h6v6 M20 4l-9 9 M18 14v6H4V6h6",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  refresh: "M20 12a8 8 0 1 1-2.3-5.7 M20 4v5h-5",
  share: "M12 3v13 M7 8l5-5 5 5 M5 14v6h14v-6",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4",
  demo: "M4 4l8 8-8 8z M12 4l8 8-8 8z",
  qr: "M4 8V5a1 1 0 0 1 1-1h3 M16 4h3a1 1 0 0 1 1 1v3 M20 16v3a1 1 0 0 1-1 1h-3 M8 20H5a1 1 0 0 1-1-1v-3 M8 8h3v3H8z M13 8h3v3h-3z M8 13h3v3H8z M14 14h2v2h-2z",
} as const;

export type UiIconName = keyof typeof UI_PATHS;

interface IconProps {
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export function StoryIcon({ kind, size = 24, strokeWidth = 1.8, className }: IconProps & { kind: StoryIconKind }) {
  return <Glyph d={STORY_ICON_PATHS[kind]} size={size} strokeWidth={strokeWidth} className={className} />;
}

export function UiIcon({ name, size = 20, strokeWidth = 2.2, className }: IconProps & { name: UiIconName }) {
  return <Glyph d={UI_PATHS[name]} size={size} strokeWidth={strokeWidth} className={className} />;
}

function Glyph({
  d,
  size,
  strokeWidth,
  className,
}: {
  d: string;
  size: number;
  strokeWidth: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d={d} />
    </svg>
  );
}

export function PlayGlyph({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 4l13 8-13 8z" fill="currentColor" />
    </svg>
  );
}

export function PauseGlyph({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4h4v16H6z M14 4h4v16h-4z" fill="currentColor" />
    </svg>
  );
}
