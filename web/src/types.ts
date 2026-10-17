export type LineKind = "bus" | "tram" | "night" | "plain";

export type StopState = "passed" | "current" | "next" | "upcoming";

export type StoryIconKind = "patron" | "oldname" | "bazaar" | "cinema" | "building" | "river" | "event";

export type PictureVariant = "photo" | "map" | "year";

export type LookDirection = "left" | "right" | "around";

export type StoryCardState = "waiting" | "playing" | "skipped";

export interface RouteStop {
  name: string;
  state: StopState;
  etaLabel?: string;
  hasStory?: boolean;
}
