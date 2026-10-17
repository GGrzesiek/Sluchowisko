import type { ReactNode } from "react";
import { ErrorBanner, NowPlayingBar } from "../components";
import { PLACEHOLDER_RIDE, PLACEHOLDER_STORY } from "../data/placeholderRide";
import { JourneyScreen } from "./JourneyScreen";
import { FindingVehicleScreen } from "./FindingVehicleScreen";
import { ManualEntryScreen } from "./ManualEntryScreen";
import { RideDeadEndScreen } from "./RideDeadEndScreen";
import { VehicleFoundScreen } from "./VehicleFoundScreen";

export interface ScreenNav {
  back: () => void;
  next: () => void;
}

export interface ScreenEntry {
  id: string;
  number: string;
  title: string;
  render: ((nav: ScreenNav) => ReactNode) | null;
  href?: string;
}

export const SCREENS: ScreenEntry[] = [
  { id: "welcome", number: "1", title: "Powitanie", render: null, href: import.meta.env.BASE_URL },
  {
    id: "manual",
    number: "1b",
    title: "Wpisz numer pojazdu",
    render: (nav) => <ManualEntryScreen onBack={nav.back} onSubmit={nav.next} />,
  },
  {
    id: "loading",
    number: "2",
    title: "Szukamy pojazdu",
    render: (nav) => (
      <FindingVehicleScreen ride={{ vehicle: PLACEHOLDER_RIDE.vehicle, line: "180" }} onCancel={nav.back} />
    ),
  },
  {
    id: "connected",
    number: "3",
    title: "Znaleziono pojazd",
    render: (nav) => <VehicleFoundScreen ride={PLACEHOLDER_RIDE} onStart={nav.next} />,
  },
  {
    id: "journey",
    number: "3C",
    title: "Przejazd · zdjęcia i tekst",
    render: (nav) => <JourneyScreen ride={PLACEHOLDER_RIDE} story={PLACEHOLDER_STORY} onClose={nav.back} />,
  },
  { id: "end", number: "7", title: "Koniec jazdy", render: null },
  {
    id: "not-found",
    number: "8",
    title: "Nie widzimy pojazdu",
    render: (nav) => (
      <RideDeadEndScreen problem="vehicleNotFound" vehicle="1234" onEnterAnother={nav.back} onStart={nav.back} />
    ),
  },
  {
    id: "no-stories",
    number: "8",
    title: "Linia bez historii",
    render: (nav) => (
      <RideDeadEndScreen problem="noRoute" vehicle="1234" line="999" onEnterAnother={nav.back} onStart={nav.back} />
    ),
  },
  {
    id: "reconnecting",
    number: "8",
    title: "Utracone połączenie",
    render: () => (
      <main className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col bg-paper p-4">
        <ErrorBanner error={{ kind: "positionLost", line: "180", lastStop: "Stare Miasto" }} />
        <NowPlayingBar
          title="Hala Mirowska: targ, ruina i znów targ"
          playing
          elapsedLabel="01:05"
          totalLabel="01:32"
          progress={0.7}
          className="mt-auto"
        />
      </main>
    ),
  },
  { id: "demo", number: "8", title: "Tryb demo", render: null },
];

export const screenHref = (screen: ScreenEntry) => screen.href ?? `#/${screen.id}`;

export const screenHash = (id: string) => `#/${id}`;

export function findScreen(hash: string): ScreenEntry | undefined {
  return SCREENS.find((s) => screenHash(s.id) === hash);
}
