import type { ReactNode } from "react";
import { UiIcon } from "./Icon";
import { SepiaImage } from "./SepiaImage";
import { cx } from "../cx";

export function MonoLabel({
  children,
  tone = "umber",
  className,
}: {
  children: ReactNode;
  tone?: "umber" | "bus";
  className?: string;
}) {
  return (
    <span
      className={cx(
        "font-mono text-xs font-semibold tracking-[0.06em]",
        tone === "bus" ? "text-bus" : "text-umber",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <h2 className="m-0 font-mono text-xs font-semibold tracking-[0.08em] text-umber">{children}</h2>;
}

export function StoryHeading({ title, lead }: { title: string; lead?: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className="m-0 text-[32px] font-extrabold leading-[1.05] tracking-[-0.01em] [font-stretch:90%]">{title}</h1>
      {lead && <p className="m-0 text-base leading-[1.4] text-umber">{lead}</p>}
    </div>
  );
}

export function LiveCaption({ label = "TERAZ", children }: { label?: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline gap-2.5">
      <MonoLabel tone="bus" className="shrink-0">
        {label}
      </MonoLabel>
      <span className="text-[15px] leading-[1.3]">{children}</span>
    </div>
  );
}

interface MapCardProps {
  label?: string;
  credit?: string;
  height?: number;
  ariaLabel: string;
  children?: ReactNode;
}

export function MapCard({
  label = "MAPA",
  credit = "© OpenStreetMap",
  height = 240,
  ariaLabel,
  children,
}: MapCardProps) {
  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className="relative shrink-0 overflow-hidden rounded-[20px] bg-[#f1efeb]"
      style={{ height }}
    >
      {children ?? <MapPlaceholder />}
      <span className="absolute right-3 top-3 flex h-6 items-center rounded-lg bg-cream px-[9px] font-mono text-[11px] font-semibold tracking-[0.06em] text-charcoal">
        {label}
      </span>
      <span className="absolute bottom-1.5 right-2 rounded bg-paper/85 px-1.5 py-px text-[9px] text-umber">
        {credit}
      </span>
    </div>
  );
}

function MapPlaceholder() {
  return (
    <svg
      viewBox="0 0 342 240"
      preserveAspectRatio="xMidYMid slice"
      className="absolute inset-0 h-full w-full"
      aria-hidden="true"
    >
      <rect width="342" height="240" fill="#F1EFEB" />
      <path d="M-20 200L120 90L260 10L380 -30L380 40L270 90L130 170L-20 260Z" fill="#AADAFF" />
      <path d="M-20 170L110 125L342 40" fill="none" stroke="#B9B4AC" strokeWidth="4" strokeLinecap="round" />
      <path d="M110 125L342 40" fill="none" stroke="#A83322" strokeWidth="4" strokeLinecap="round" />
      <circle cx="300" cy="56" r="5" fill="#fff" stroke="#A83322" strokeWidth="3" />
    </svg>
  );
}

interface PhotoFigureProps {
  src?: string;
  alt: string;
  year: string;
  caption: string;
  height?: number;
  radius?: number;
  layout?: "row" | "stacked";
}

export function PhotoFigure({ src, alt, year, caption, height = 200, radius = 16, layout = "row" }: PhotoFigureProps) {
  const stacked = layout === "stacked";
  return (
    <figure className={cx("m-0 flex flex-col", stacked ? "gap-1.5" : "gap-2")}>
      <div className="overflow-hidden bg-ink" style={{ height, borderRadius: radius }}>
        {src ? (
          <SepiaImage src={src} alt={alt} />
        ) : (
          <div role="img" aria-label={alt} className="h-full w-full bg-gradient-to-br from-hair to-ink" />
        )}
      </div>
      <figcaption className={cx("flex", stacked ? "flex-col gap-0.5" : "items-baseline gap-2.5")}>
        <MonoLabel tone="bus" className="shrink-0">
          {year}
        </MonoLabel>
        <span className={cx("text-umber", stacked ? "text-[13px] leading-[1.3]" : "text-sm leading-[1.35]")}>
          {caption}
        </span>
      </figcaption>
    </figure>
  );
}

export function FactGrid({ facts }: { facts: Array<{ value: string; label: string }> }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {facts.map((f) => (
        <div key={f.label} className="flex flex-col gap-1 rounded-[14px] bg-puff px-2.5 pb-3 pt-2.5">
          <span className="text-xl font-black leading-none [font-stretch:80%]">{f.value}</span>
          <span className="font-mono text-[10px] font-semibold tracking-[0.06em] text-umber">{f.label}</span>
        </div>
      ))}
    </div>
  );
}

export function Callout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-[20px] bg-sand p-4">
      <UiIcon name="eye" size={22} className="mt-px shrink-0 text-bus" />
      <p className="m-0 text-[15px] leading-[1.45]">
        <b className="font-extrabold">{title}</b> {children}
      </p>
    </div>
  );
}

export function Prose({ children }: { children: ReactNode }) {
  return <p className="m-0 text-[17px] leading-[1.55]">{children}</p>;
}

export interface ChronoEvent {
  year: string;
  text: string;
  tone?: "past" | "loss" | "now";
}

export function StoryTimeline({ events, title = "OŚ CZASU" }: { events: ChronoEvent[]; title?: string }) {
  return (
    <div className="flex flex-col gap-3 pt-2">
      <SectionLabel>{title}</SectionLabel>
      <ol className="relative m-0 flex list-none flex-col p-0">
        <span aria-hidden="true" className="absolute bottom-2 left-1.5 top-2 w-[3px] bg-road" />
        {events.map((ev) => {
          const tone = ev.tone ?? "past";
          return (
            <li key={`${ev.year}-${ev.text}`} className="relative flex gap-4 pb-3.5">
              <span
                className={cx(
                  "relative mt-1 box-border h-[15px] w-[15px] shrink-0",
                  tone === "loss" && "bg-bus",
                  tone === "past" && "bg-ink",
                  tone === "now" && "border-[2.5px] border-bus bg-paper",
                )}
              />
              <div className="flex flex-col gap-0.5">
                <MonoLabel tone={tone === "loss" ? "bus" : "umber"}>{ev.year}</MonoLabel>
                <span className="text-[15px] leading-[1.35]">{ev.text}</span>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function SourceList({ sources, note }: { sources: Array<{ label: string; href: string }>; note?: string }) {
  return (
    <div className="flex flex-col">
      <h2 className="m-0 mb-1 font-mono text-xs font-semibold tracking-[0.08em] text-umber">ŹRÓDŁA</h2>
      {sources.map((s) => (
        <a
          key={s.href}
          href={s.href}
          target="_blank"
          rel="noreferrer"
          className="flex min-h-12 items-center justify-between gap-3 border-b border-ground text-[15px] font-semibold text-charcoal no-underline"
        >
          <span>{s.label}</span>
          <UiIcon name="external" size={18} className="shrink-0" />
        </a>
      ))}
      {note && <span className="mt-2.5 text-xs leading-[1.4] text-umber">{note}</span>}
    </div>
  );
}
