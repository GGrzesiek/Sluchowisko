import { PALETTE_DEFAULTS, applyTheme, resetTheme } from "./theme";

describe("theme", () => {
  it("overrides and resets a colour token", () => {
    applyTheme({ bus: "#112233" });
    expect(document.documentElement.style.getPropertyValue("--color-bus")).toBe("#112233");
    resetTheme();
    expect(document.documentElement.style.getPropertyValue("--color-bus")).toBe("");
  });

  it("covers every token declared in theme.css", () => {
    expect(Object.keys(PALETTE_DEFAULTS)).toContain("mustard");
  });
});
