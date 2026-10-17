import type { ReactNode } from "react";
import { PLACEHOLDER_RIDE, PLACEHOLDER_STORY } from "../data/placeholderRide";
import { JourneyScreen } from "./JourneyScreen";
import { FindingVehicleScreen } from "./FindingVehicleScreen";
import { ManualEntryScreen } from "./ManualEntryScreen";
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
  { id: "no-stories", number: "8", title: "Linia bez historii", render: null },
  { id: "reconnecting", number: "8", title: "Utracone połączenie", render: null },
  { id: "demo", number: "8", title: "Tryb demo", render: null },
];

export const screenHref = (screen: ScreenEntry) => screen.href ?? `#/${screen.id}`;

export const screenHash = (id: string) => `#/${id}`;

export function findScreen(hash: string): ScreenEntry | undefined {
  return SCREENS.find((s) => screenHash(s.id) === hash);
}
