import type { ComponentType } from "react";
import { ManualEntryScreen } from "./ManualEntryScreen";

export interface ScreenProps {
  onBack: () => void;
  onSubmit: (value: string) => void;
}

export interface ScreenEntry {
  id: string;
  number: string;
  title: string;
  Component: ComponentType<ScreenProps> | null;
}

export const SCREENS: ScreenEntry[] = [
  { id: "welcome", number: "1", title: "Powitanie", Component: null },
  { id: "manual", number: "1b", title: "Wpisz numer pojazdu", Component: ManualEntryScreen },
  { id: "loading", number: "2", title: "Szukamy pojazdu", Component: null },
  { id: "connected", number: "3", title: "Znaleziono pojazd", Component: null },
  { id: "journey", number: "3C", title: "Linia przystanków", Component: null },
  { id: "story-map", number: "4B", title: "Przejazd · mapa i historia", Component: null },
  { id: "end", number: "7", title: "Koniec jazdy", Component: null },
  { id: "no-stories", number: "8", title: "Linia bez historii", Component: null },
  { id: "reconnecting", number: "8", title: "Utracone połączenie", Component: null },
  { id: "demo", number: "8", title: "Tryb demo", Component: null },
];

export const screenHash = (id: string) => `#/${id}`;

export function findScreen(hash: string): ScreenEntry | undefined {
  return SCREENS.find((s) => screenHash(s.id) === hash);
}
