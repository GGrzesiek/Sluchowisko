import { useId } from "react";
import { StoryIcon } from "./Icon";
import { Grain } from "./Grain";
import { SepiaImage } from "./SepiaImage";
import { cx } from "../cx";
import type { PictureVariant, StoryIconKind } from "../types";

interface PictureProps {
  variant: PictureVariant;
  height?: number;
  radius?: number;
  year?: string;
  icon?: StoryIconKind;
  caption?: string;
  credit?: string | false;
  src?: string;
  alt?: string;
  photoCount?: number;
  photoIndex?: number;
  className?: string;
}

const DEFAULT_YEAR: Record<PictureVariant, string> = { photo: "1936", map: "1935", year: "1902" };
const DEFAULT_CREDIT: Record<PictureVariant, string> = {
  photo: "Fot. NN, {year} · NAC / Wikimedia Commons · domena publiczna",
  map: "Fotoplan 1935 · m.st. Warszawa · otwarte dane",
  year: "",
};

export function Picture({
  variant,
  height = 280,
  radius = 20,
  year,
  icon = "bazaar",
  caption = "Hala Mirowska · otwarcie",
  credit,
  src,
  alt,
  photoCount = 1,
  photoIndex = 0,
  className,
}: PictureProps) {
  const shownYear = year ?? DEFAULT_YEAR[variant];
  const big = height >= 200;
  const creditText = credit === false ? "" : (credit ?? DEFAULT_CREDIT[variant].replace("{year}", shownYear));
  return (
    <div
      className={cx("relative w-full overflow-hidden", variant === "year" ? "bg-sand" : "bg-[#77746d]", className)}
      style={{ height, borderRadius: radius }}
    >
      {variant === "photo" && (
        <>
          {src ? <SepiaImage src={src} alt={alt ?? ""} /> : <PhotoPlaceholder />}
          {big && (
            <span className="absolute left-3 top-3 rounded-[10px] bg-cream px-3 py-1 font-serif text-2xl font-semibold leading-[1.1] text-hair">
              {shownYear}
            </span>
          )}
          {big && !src && (
            <span className="absolute right-3 top-3.5 rounded-md bg-charcoal/80 px-2 py-[3px] text-[10px] font-bold uppercase tracking-[0.08em] text-cream">
              Miejsce na zdjęcie
            </span>
          )}
          {photoCount > 1 && big && <PhotoDots count={photoCount} index={photoIndex} />}
        </>
      )}
      {variant === "map" && (
        <>
          <MapPlaceholder />
          {big && (
            <span className="absolute left-3 top-3 rounded-[10px] bg-cream px-3 py-1.5 font-serif text-lg font-semibold leading-[1.1] text-charcoal">
              Warszawa z góry, 1935
            </span>
          )}
        </>
      )}
      {variant === "year" && <YearCard year={shownYear} icon={icon} caption={caption} height={height} />}
      {creditText && variant !== "year" && <PhotoCredit text={creditText} />}
    </div>
  );
}

export function PhotoCredit({ text, overlay = true }: { text: string; overlay?: boolean }) {
  return (
    <span
      className={cx(
        "block truncate text-[11px] leading-[1.3]",
        overlay ? "absolute inset-x-0 bottom-0 bg-charcoal/80 px-3 py-1.5 text-cream" : "text-umber",
      )}
    >
      {text}
    </span>
  );
}

export function PhotoDots({ count, index }: { count: number; index: number }) {
  return (
    <div
      role="img"
      aria-label={`Zdjęcie ${index + 1} z ${count}`}
      className="absolute inset-x-0 bottom-[34px] flex justify-center gap-1.5"
    >
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className={cx("h-1.5 rounded-full", i === index ? "w-[18px] bg-cream" : "w-1.5 bg-cream/60")} />
      ))}
    </div>
  );
}

function YearCard({
  year,
  icon,
  caption,
  height,
}: {
  year: string;
  icon: StoryIconKind;
  caption: string;
  height: number;
}) {
  const big = height >= 200;
  const showIcon = height >= 100;
  const yearSize = Math.round(Math.min(showIcon ? height * 0.42 : height * 0.36, 128));
  return (
    <>
      <Grain opacity={0.45} baseFrequency={0.85} />
      <span className="absolute inset-3 rounded-xl border-[1.5px] border-hair/30" />
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 text-hair">
        {showIcon && (
          <span
            className="flex items-center justify-center rounded-full border-2 border-hair"
            style={{ width: big ? 52 : 36, height: big ? 52 : 36 }}
          >
            <StoryIcon kind={icon} size={26} />
          </span>
        )}
        <span className="font-serif font-medium leading-none tracking-[-0.02em]" style={{ fontSize: yearSize }}>
          {year}
        </span>
        {big && <span className="text-xs font-bold uppercase tracking-[0.14em]">{caption}</span>}
      </div>
    </>
  );
}

function PhotoPlaceholder() {
  const id = `photo-grain-${useId().replace(/:/g, "")}`;
  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 358 280"
      preserveAspectRatio="xMidYMid slice"
      className="absolute inset-0"
      role="img"
      aria-label="Miejsce na archiwalne zdjęcie"
    >
      <rect width="358" height="280" fill="#CDB591" />
      <rect width="358" height="120" fill="#DCC8A6" />
      <path d="M0 120h358v160H0z" fill="#9E8259" />
      <path d="M-10 132L60 82h250l60 50z" fill="#5E4429" />
      <path d="M20 132h330v74H20z" fill="#7A5B39" />
      <path
        d="M40 206v-46a14 14 0 0 1 28 0v46 M86 206v-46a14 14 0 0 1 28 0v46 M132 206v-46a14 14 0 0 1 28 0v46 M178 206v-46a14 14 0 0 1 28 0v46 M224 206v-46a14 14 0 0 1 28 0v46 M270 206v-46a14 14 0 0 1 28 0v46"
        fill="#E3D2B2"
      />
      <path
        d="M40 182h28 M86 182h28 M132 182h28 M178 182h28 M224 182h28 M270 182h28 M54 146v60 M100 146v60 M146 146v60 M192 146v60 M238 146v60 M284 146v60"
        stroke="#7A5B39"
        strokeWidth="2"
      />
      <path d="M150 82l35-30 35 30z" fill="#4A3420" />
      <path d="M0 206h358v6H0z" fill="#5E4429" />
      <path d="M10 232h70l-8-14H18z M110 238h80l-8-16h-64z M230 234h90l-8-14h-74z" fill="#EADBC0" />
      <path
        d="M14 232v22 M76 232v22 M114 238v24 M186 238v24 M234 234v22 M316 234v22"
        stroke="#4A3420"
        strokeWidth="2.5"
      />
      <g fill="#3E2C18">
        <ellipse cx="96" cy="250" rx="5" ry="13" />
        <circle cx="96" cy="234" r="5" />
        <ellipse cx="206" cy="256" rx="5" ry="14" />
        <circle cx="206" cy="239" r="5" />
        <ellipse cx="336" cy="252" rx="5" ry="13" />
        <circle cx="336" cy="236" r="5" />
      </g>
      <ellipse cx="216" cy="258" rx="4" ry="11" fill="#4A3420" />
      <circle cx="216" cy="245" r="4" fill="#4A3420" />
      <filter id={id}>
        <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="3" stitchTiles="stitch" />
        <feColorMatrix values="0 0 0 0 0.3  0 0 0 0 0.22  0 0 0 0 0.12  0 0 0 0.6 0" />
      </filter>
      <rect width="358" height="280" filter={`url(#${id})`} opacity="0.55" />
    </svg>
  );
}

function MapPlaceholder() {
  const id = `map-grain-${useId().replace(/:/g, "")}`;
  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 358 280"
      preserveAspectRatio="xMidYMid slice"
      className="absolute inset-0"
      role="img"
      aria-label="Czarno-białe zdjęcie lotnicze okolicy z 1935 roku z pinezką na miejscu historii"
    >
      <rect width="358" height="280" fill="#77746D" />
      <g transform="rotate(-14 179 140)">
        <path
          d="M-60 -40h80v70h-80z M40 -40h90v70H40z M150 -40h80v70h-80z M250 -40h120v70H250z M-60 50h80v80h-80z M40 50h90v80H40z M250 50h120v80H250z M-60 150h80v80h-80z M40 150h90v80H40z M150 150h80v80h-80z M250 150h120v80H250z M-60 250h80v80h-80z M40 250h90v80H40z M150 250h80v80h-80z M250 250h120v80H250z"
          fill="#A9A59C"
        />
        <path
          d="M-50 -30h60v50h-60z M50 -30h70v50H50z M160 -30h60v50h-60z M260 -30h100v50H260z M-50 60h60v60h-60z M50 60h70v60H50z M260 60h100v60H260z M-50 160h60v60h-60z M50 160h70v60H50z M160 160h60v60h-60z M260 160h100v60H260z M-50 260h60v60h-60z M50 260h70v60H50z M260 260h100v60H260z"
          fill="#5E5B55"
        />
        <path d="M150 50h80v80h-80z" fill="#C9C5BB" />
        <path d="M158 58h64v64h-64z" fill="#8E8A82" />
        <path d="M158 89h64" stroke="#C9C5BB" strokeWidth="3" />
        <path d="M-80 140h520" stroke="#D3CFC6" strokeWidth="12" />
        <path d="M140 -60v420" stroke="#C3BFB6" strokeWidth="7" />
      </g>
      <g fill="#3F3D39">
        <circle cx="30" cy="236" r="9" />
        <circle cx="46" cy="248" r="8" />
        <circle cx="22" cy="258" r="10" />
        <circle cx="58" cy="264" r="9" />
        <circle cx="40" cy="270" r="8" />
      </g>
      <filter id={id}>
        <feTurbulence type="fractalNoise" baseFrequency="1.3" numOctaves="2" stitchTiles="stitch" />
        <feColorMatrix values="0 0 0 0 0.2  0 0 0 0 0.2  0 0 0 0 0.2  0 0 0 0.7 0" />
      </filter>
      <rect width="358" height="280" filter={`url(#${id})`} opacity="0.6" />
      <circle cx="190" cy="132" r="30" fill="none" stroke="#DBA250" strokeWidth="2.5" strokeDasharray="4 5" />
      <path
        d="M190 132s-16-14-16-26a16 16 0 0 1 32 0c0 12-16 26-16 26z"
        fill="#A83322"
        stroke="#F9EDD1"
        strokeWidth="2.5"
      />
      <circle cx="190" cy="106" r="5.5" fill="#F9EDD1" />
    </svg>
  );
}
