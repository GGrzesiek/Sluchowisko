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

export interface TimelineItem {
  year: string;
  text: string;
  sources?: number[];
}

export type StoryBlock =
  | { type: "paragraph"; text: string; sources?: number[] }
  | { type: "image"; photo: number }
  | { type: "timeline"; items: TimelineItem[] };

export interface StoryContent {
  title: string;
  photos: [StoryPhoto, ...StoryPhoto[]];
  body: StoryBody;
  blocks?: StoryBlock[];
  sources: StorySource[];
  audio?: string;
}
