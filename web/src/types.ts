export type LineKind = "bus" | "tram" | "night" | "plain";

export type StopState = "passed" | "current" | "next" | "upcoming";

export type StoryIconKind = "patron" | "oldname" | "bazaar" | "cinema" | "building" | "river" | "event";

export type PictureVariant = "photo" | "map" | "year";

export type LookDirection = "left" | "right" | "around";

export type StoryCardState = "waiting" | "playing" | "skipped";

export interface RouteStop {
  name: string;
  state: StopState;
  etaMinutes?: number;
  hasStory?: boolean;
}

export interface RideInfo {
  vehicle: string;
  line?: string;
  destination: string;
  stops: RouteStop[];
}

export interface StoryPhoto {
  src?: string;
  alt: string;
  year: string;
  caption: string;
  credit: string;
}

export interface StorySource {
  label: string;
  href: string;
}

export type StoryBody = { format: "plain"; text: string };

export type TimelineTone = "past" | "loss" | "now";

export interface TimelineItem {
  year: string;
  text: string;
  tone?: TimelineTone;
  sources?: number[];
}

export interface FactItem {
  value: string;
  label: string;
  sources?: number[];
}

export interface StoryCardInfo {
  icon: StoryIconKind;
  year?: string;
}

export type StoryBlock =
  | { type: "paragraph"; text: string; sources?: number[] }
  | { type: "image"; photo: number }
  | { type: "timeline"; items: TimelineItem[] }
  | { type: "facts"; items: [FactItem, FactItem, FactItem] }
  | { type: "callout"; title: string; text: string; sources?: number[] };

export interface StoryContent {
  title: string;
  lead?: string;
  card?: StoryCardInfo;
  sourceNote?: string;
  photos: [StoryPhoto, ...StoryPhoto[]];
  body: StoryBody;
  blocks?: StoryBlock[];
  sources: StorySource[];
  audio?: string;
}
