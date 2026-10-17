export const PALETTE_DEFAULTS = {
  paper: "#f5f2eb",
  sand: "#f6e5c3",
  charcoal: "#282b2c",
  bus: "#a83322",
  "bus-shade": "#932e1f",
  cream: "#f9edd1",
  ink: "#2d221e",
  "ink-deep": "#171413",
  glass: "#9dafb4",
  "glass-top": "#4f575a",
  tyre: "#2b2320",
  chrome: "#b2b0ac",
  ground: "#d8d4ce",
  road: "#c8c2b4",
  puff: "#efece4",
  umber: "#5e4f49",
  mustard: "#dba250",
  navy: "#263b4d",
  olive: "#626141",
  hair: "#503a29",
} as const;

export type PaletteKey = keyof typeof PALETTE_DEFAULTS;
export type Palette = Record<PaletteKey, string>;

export function applyTheme(overrides: Partial<Palette>, root: HTMLElement = document.documentElement): void {
  for (const [key, value] of Object.entries(overrides)) {
    root.style.setProperty(`--color-${key}`, value);
  }
}

export function resetTheme(root: HTMLElement = document.documentElement): void {
  for (const key of Object.keys(PALETTE_DEFAULTS)) {
    root.style.removeProperty(`--color-${key}`);
  }
}
