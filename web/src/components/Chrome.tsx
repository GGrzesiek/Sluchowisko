import type { ReactNode } from "react";
import { Button, IconButton } from "./Button";
import { LineBadge, LineChip, VehicleTag } from "./LineBadge";
import { Thumb } from "./Story";
import { UiIcon } from "./Icon";
import { cx } from "../cx";
import type { StoryIconKind } from "../types";

export function VehicleHeader({
  vehicle,
  destination,
  onClose,
}: {
  vehicle: string;
  destination: string;
  onClose?: () => void;
}) {
  return (
    <div className="flex h-12 items-center gap-3">
      <VehicleTag number={vehicle} />
      <span className="grow whitespace-nowrap text-[17px] font-extrabold">→ {destination}</span>
      {onClose && (
        <button
          type="button"
          aria-label="Zakończ przejazd"
          onClick={onClose}
          className="flex h-11 w-[60px] shrink-0 items-center justify-center rounded-[14px] bg-bus text-cream"
        >
          <UiIcon name="close" size={22} strokeWidth={1.8} />
        </button>
      )}
    </div>
  );
}

export function BackBar({ onBack }: { onBack?: () => void }) {
  return (
    <div className="flex h-12 items-center">
      <IconButton label="Wstecz" onClick={onBack}>
        <UiIcon name="arrowLeft" size={22} />
      </IconButton>
    </div>
  );
}

export function StatusBanner({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div role="status" className="flex min-h-14 items-center gap-3 rounded-2xl bg-mustard px-3.5 py-2.5 text-charcoal">
      <UiIcon name="refresh" size={22} />
      <div className="flex flex-col">
        <span className="text-base font-extrabold">{title}</span>
        {children && <span className="text-[13px] font-medium">{children}</span>}
      </div>
    </div>
  );
}

export function DemoBadge({ children = "DEMO · ODTWARZANIE 10×" }: { children?: ReactNode }) {
  return (
    <span className="inline-flex h-9 items-center gap-2 rounded-[10px] bg-charcoal px-3 text-[13px] font-black tracking-[0.08em] text-paper">
      <UiIcon name="demo" size={16} strokeWidth={2.4} />
      <span>{children}</span>
    </span>
  );
}

export function DirectionHeader({ line, destination }: { line: string; destination: string }) {
  return (
    <div className="flex min-h-16 items-center gap-3">
      <LineBadge line={line} size="md" />
      <div className="flex grow flex-col gap-0.5">
        <span className="text-xs font-bold uppercase tracking-[0.08em] text-umber">Kierunek</span>
        <span className="text-xl font-extrabold">{destination}</span>
      </div>
    </div>
  );
}

export function AppLogo({ name = "Linia Czasu" }: { name?: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
        <rect width="28" height="28" rx="8" fill="#A83322" />
        <path d="M14 7v14" stroke="#F9EDD1" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="14" cy="8" r="3.2" fill="#DBA250" />
        <circle cx="14" cy="20" r="3" fill="#A83322" stroke="#F9EDD1" strokeWidth="2.2" />
      </svg>
      <span className="text-base font-bold">{name}</span>
    </div>
  );
}

export function VehicleInput({
  value,
  onChange,
  autoFocus,
}: {
  value: string;
  onChange?: (v: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="vehicle-number" className="text-[15px] font-bold">
        Numer boczny pojazdu
      </label>
      <input
        id="vehicle-number"
        inputMode="numeric"
        autoComplete="off"
        maxLength={4}
        autoFocus={autoFocus}
        aria-describedby="vehicle-number-hint"
        placeholder="np. 1234"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className="box-border h-16 rounded-2xl border-[1.5px] border-road bg-cream px-[18px] text-[30px] font-extrabold tracking-[0.06em] text-charcoal outline-none [font-stretch:85%] focus:border-bus"
      />
      <div className="flex items-center gap-3.5 rounded-2xl bg-puff p-3">
        <svg
          width="132"
          height="92"
          viewBox="0 0 132 92"
          role="img"
          aria-label="Numer boczny jest wypisany nad drzwiami, w środku pojazdu"
          className="shrink-0"
        >
          <rect x="1" y="1" width="130" height="90" rx="10" fill="#F9EDD1" stroke="#C8C2B4" strokeWidth="1.5" />
          <rect x="10" y="12" width="34" height="38" rx="4" fill="#9DAFB4" stroke="#5E4F49" strokeWidth="1.5" />
          <rect x="88" y="12" width="34" height="38" rx="4" fill="#9DAFB4" stroke="#5E4F49" strokeWidth="1.5" />
          <rect x="52" y="30" width="28" height="60" rx="2" fill="none" stroke="#5E4F49" strokeWidth="1.5" />
          <path d="M66 30v60" stroke="#5E4F49" strokeWidth="1.5" />
          <rect x="50" y="10" width="32" height="14" rx="3" fill="#282B2C" />
          <text
            x="66"
            y="20.5"
            textAnchor="middle"
            fontFamily="Archivo Variable, sans-serif"
            fontWeight="800"
            fontSize="10"
            fill="#F9EDD1"
          >
            1234
          </text>
          <circle cx="66" cy="17" r="16" fill="none" stroke="#A83322" strokeWidth="2.5" />
          <path d="M10 72h34 M88 72h34" stroke="#C8C2B4" strokeWidth="6" strokeLinecap="round" />
        </svg>
        <span id="vehicle-number-hint" className="text-sm leading-[1.35]">
          Szukaj nad drzwiami albo przy kabinie kierowcy. To 4 cyfry.
        </span>
      </div>
    </div>
  );
}

interface StoryListItemProps {
  title: string;
  year: string;
  type: string;
  icon: StoryIconKind;
  onClick?: () => void;
}

export function StoryListItem({ title, year, type, icon, onClick }: StoryListItemProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="box-border flex min-h-[66px] w-full items-center gap-3 rounded-2xl bg-cream py-[5px] pl-[5px] pr-3 text-left text-charcoal"
    >
      <Thumb thumb={{ variant: "year", year, icon }} size={56} />
      <div className="flex min-w-0 grow flex-col gap-0.5">
        <span className="font-serif text-[17px] font-semibold leading-[1.15]">{title}</span>
        <span className="text-[13px] text-umber">
          {year} · {type}
        </span>
      </div>
      <UiIcon name="chevron" size={18} />
    </button>
  );
}

export function EmptyLineNotice({ line, suggestion }: { line: string; suggestion: string }) {
  return (
    <div className="flex flex-col gap-4">
      <span className="font-condensed inline-flex h-11 min-w-[70px] items-center justify-center self-start rounded-[10px] border-2 border-dashed border-umber px-2.5 text-[32px] font-black text-umber">
        {line}
      </span>
      <div className="text-[26px] font-extrabold leading-[1.15] tracking-[-0.02em]">
        Nie mamy jeszcze historii dla linii {line}.
      </div>
      <div className="text-base leading-[1.4] text-umber">
        Spróbuj linii {suggestion}. Mija sześć miejsc z historią.
      </div>
      <Button size="md" className={cx("w-full")}>
        Spróbuj linii <LineChip line={suggestion} />
      </Button>
    </div>
  );
}
