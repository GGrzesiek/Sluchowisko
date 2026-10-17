import { useEffect, useState } from "react";
import {
  Button,
  LineBadge,
  LookChip,
  Picture,
  RouteStrip,
  StoryCard,
  StoryIcon,
  UiIcon,
  StoryMarker,
  VehicleTag,
  PlayButton,
  PlayGlyph,
  AppLogo,
  BackBar,
  Callout,
  DemoBadge,
  DirectionHeader,
  EmptyLineNotice,
  FactGrid,
  LiveCaption,
  MapCard,
  NowPlayingBar,
  PhotoFigure,
  Prose,
  SourceList,
  StatusBanner,
  StoryHeading,
  StoryListItem,
  StoryTimeline,
  VehicleHeader,
  VehicleInput,
  STORY_ICON_LABELS,
} from "./components";
import { PALETTE_DEFAULTS, applyTheme, resetTheme, type PaletteKey } from "./theme";
import { SCREENS, findScreen, screenHash } from "./screens/registry";
import type { RouteStop, StoryIconKind } from "./types";

const STOPS: RouteStop[] = [
  { name: "Centrum", state: "passed" },
  { name: "Krucza", state: "passed" },
  { name: "Muzeum Narodowe", state: "passed" },
  { name: "Most Poniatowskiego", state: "current", hasStory: true },
  { name: "Rondo Waszyngtona", state: "next", etaMinutes: 2 },
  { name: "Berezyńska", state: "next" },
];

const ICONS = Object.keys(STORY_ICON_LABELS) as StoryIconKind[];

function Section({
  title,
  children,
  className = "",
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`flex flex-col gap-5 rounded-3xl bg-paper p-7 ${className}`}>
      <h2 className="m-0 text-[13px] font-extrabold uppercase tracking-[0.1em] text-umber">{title}</h2>
      {children}
    </section>
  );
}

function ScreenIndex() {
  return (
    <Section title="Ekrany">
      <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 lg:grid-cols-3">
        {SCREENS.map((screen) => (
          <li key={screen.id}>
            {screen.render ? (
              <a
                href={screenHash(screen.id)}
                className="flex items-center gap-3 rounded-2xl bg-cream p-3.5 text-charcoal no-underline"
              >
                <ScreenNumber>{screen.number}</ScreenNumber>
                <span className="grow text-base font-extrabold">{screen.title}</span>
                <UiIcon name="chevron" size={18} />
              </a>
            ) : (
              <div
                aria-disabled="true"
                className="flex items-center gap-3 rounded-2xl border-[1.5px] border-dashed border-road p-3.5 text-umber"
              >
                <ScreenNumber>{screen.number}</ScreenNumber>
                <span className="grow text-base font-bold">{screen.title}</span>
                <span className="font-mono text-[11px] font-semibold tracking-[0.06em]">WKRÓTCE</span>
              </div>
            )}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function ScreenNumber({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-condensed flex h-9 min-w-9 items-center justify-center rounded-[9px] bg-charcoal px-2 text-[22px] font-black text-cream">
      {children}
    </span>
  );
}

function PaletteEditor() {
  const [values, setValues] = useState<Record<string, string>>({ ...PALETTE_DEFAULTS });
  const change = (key: PaletteKey, value: string) => {
    setValues((v) => ({ ...v, [key]: value }));
    applyTheme({ [key]: value });
  };
  const reset = () => {
    resetTheme();
    setValues({ ...PALETTE_DEFAULTS });
  };
  return (
    <Section title="Paleta (na żywo)">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-10">
        {(Object.keys(PALETTE_DEFAULTS) as PaletteKey[]).map((key) => (
          <label key={key} className="flex flex-col gap-1 text-xs font-bold">
            <input
              type="color"
              value={values[key]}
              onChange={(e) => change(key, e.target.value)}
              className="h-10 w-full cursor-pointer rounded-lg border border-road bg-transparent"
            />
            {key}
          </label>
        ))}
      </div>
      <Button variant="secondary" onClick={reset} className="self-start">
        Przywróć domyślne
      </Button>
    </Section>
  );
}

function goHome() {
  window.location.hash = "";
}

export function App() {
  const hash = useHashRoute();
  const screen = findScreen(hash);
  if (screen?.render) {
    return screen.render({ back: goHome, next: goHome });
  }
  return <Showcase />;
}

function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const update = () => setHash(window.location.hash);
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return hash;
}

function Showcase() {
  const [playing, setPlaying] = useState(true);
  return (
    <main className="min-h-screen bg-puff p-4 text-charcoal sm:p-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <h1 className="m-0 text-3xl font-extrabold">Muzeum w autobusie · komponenty</h1>
        <ScreenIndex />
        <PaletteEditor />
        <div className="grid gap-6 lg:grid-cols-3">
          <Section title="Numer linii">
            <div className="flex flex-wrap items-end gap-4">
              <LineBadge line="180" kind="bus" />
              <LineBadge line="17" kind="tram" />
              <LineBadge line="N12" kind="night" />
            </div>
            <div className="flex items-center gap-3">
              <LineBadge line="180" kind="bus" size="sm" />
              <LineBadge line="17" kind="tram" size="sm" />
              <LineBadge line="523" kind="plain" size="sm" />
            </div>
            <VehicleTag number="1234" />
          </Section>
          <Section title="Znaczniki i chipy">
            <StoryMarker title="Hala Mirowska" distanceLabel="za 2 przystanki" icon="bazaar" />
            <div className="flex flex-wrap gap-2.5">
              <LookChip direction="left" label="Po lewej, za chwilę" />
              <LookChip direction="right" label="Po prawej" />
              <LookChip direction="around" label="Wokół Ciebie" active={false} />
            </div>
          </Section>
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <Section title="Karta historii" className="lg:col-span-2">
            <div className="grid gap-4 md:grid-cols-3">
              <StoryCard
                state="waiting"
                title="Hala Mirowska: targ, ruina i znów targ"
                etaLabel="za ~1 min"
                thumb={{ variant: "photo" }}
              />
              <StoryCard
                state="playing"
                title="Kino Muranów"
                elapsedLabel="0:48"
                progress={0.52}
                thumb={{ variant: "year", year: "1951", icon: "cinema" }}
              />
              <StoryCard state="skipped" title="Bazar Różyckiego" thumb={{ variant: "map" }} onClick={() => {}} />
            </div>
          </Section>
          <Section title="Przyciski">
            <Button icon={<PlayGlyph />}>Ruszamy</Button>
            <Button variant="secondary">Czytaj więcej</Button>
            <PlayButton playing={playing} onToggle={() => setPlaying((p) => !p)} />
          </Section>
        </div>
        <Section title="Obszar zdjęcia · zawsze wypełniony">
          <div className="grid gap-6 md:grid-cols-3">
            <Picture variant="photo" height={260} year="1936" photoCount={3} />
            <Picture variant="map" height={260} />
            <Picture variant="year" height={260} year="1902" icon="bazaar" caption="Hala Mirowska · otwarcie" />
          </div>
        </Section>
        <div className="grid gap-6 lg:grid-cols-3">
          <Section title="Ikony typów historii" className="lg:col-span-2">
            <div className="grid grid-cols-4 gap-3 md:grid-cols-7">
              {ICONS.map((kind) => (
                <div key={kind} className="flex flex-col items-center gap-2 text-center text-[13px] font-bold">
                  <span className="flex h-16 w-16 items-center justify-center rounded-full bg-sand text-hair">
                    <StoryIcon kind={kind} size={30} />
                  </span>
                  {STORY_ICON_LABELS[kind]}
                </div>
              ))}
            </div>
          </Section>
        </div>
        <Section title="Pasek trasy">
          <RouteStrip stops={STOPS} className="max-w-[342px]" />
        </Section>
        <Section title="Ekran przejazdu · mapa i historia">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="flex max-w-[342px] flex-col gap-5">
              <VehicleHeader vehicle="1234" destination="Dworzec Wileński" onClose={() => {}} />
              <MapCard ariaLabel="Mapa okolicy" />
              <LiveCaption>Most Poniatowskiego, nad Wisłą</LiveCaption>
              <PhotoFigure
                alt="Pocztówka"
                year="1914"
                caption="Pocztówka „Warszawa. Trzeci most”"
                height={220}
                radius={20}
              />
              <StoryHeading
                title="Trzeci most, budowany trzy razy"
                lead="Wysadzany w obu wojnach światowych i za każdym razem odbudowywany."
              />
              <FactGrid
                facts={[
                  { value: "1914", label: "OTWARCIE" },
                  { value: "506 m", label: "DŁUGOŚĆ" },
                  { value: "8", label: "PRZĘSEŁ" },
                ]}
              />
              <Prose>Most na przedłużeniu Alej Jerozolimskich budowano w latach 1904–1914.</Prose>
              <div className="grid grid-cols-2 gap-2.5">
                <PhotoFigure alt="Odbudowa" year="1945" caption="Odbudowa" height={140} radius={14} layout="stacked" />
                <PhotoFigure
                  alt="Tramwaj"
                  year="22.07.1946"
                  caption="Pierwszy tramwaj"
                  height={140}
                  radius={14}
                  layout="stacked"
                />
              </div>
              <Callout title="Wyjrzyj przez okno.">Ozdobnej balustrady nie odbudowano.</Callout>
              <StoryTimeline
                events={[
                  { year: "1904", text: "Początek budowy na przedłużeniu Alej Jerozolimskich." },
                  { year: "1915", text: "Wycofujący się Rosjanie wysadzają dwa filary.", tone: "loss" },
                  { year: "dziś", text: "Przejeżdżasz nim właśnie teraz.", tone: "now" },
                ]}
              />
              <SourceList
                sources={[
                  {
                    label: "Most Poniatowskiego · Wikipedia",
                    href: "https://pl.wikipedia.org/wiki/Most_Poniatowskiego",
                  },
                ]}
                note="Zdjęcia: Wikimedia Commons, domena publiczna."
              />
              <NowPlayingBar
                title="Trzeci most"
                playing={playing}
                elapsedLabel="02:05"
                totalLabel="04:10"
                progress={0.5}
                onToggle={() => setPlaying((p) => !p)}
              />
            </div>
            <div className="flex max-w-[342px] flex-col gap-5">
              <AppLogo />
              <BackBar />
              <VehicleInput value="" onChange={() => {}} />
              <StoryListItem title="Hala Mirowska" year="1902" type="Bazar / targ" icon="bazaar" />
              <StatusBanner title="Łączymy ponownie…">Historia gra dalej.</StatusBanner>
              <DirectionHeader line="180" destination="Dworzec Wileński" />
              <DemoBadge />
              <Button variant="ghost">Wyjdź z demo</Button>
              <EmptyLineNotice line="523" suggestion="180" />
            </div>
          </div>
        </Section>
      </div>
    </main>
  );
}
