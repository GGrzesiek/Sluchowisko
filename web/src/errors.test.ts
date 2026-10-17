import { mostImportantError } from "./errors";

describe("mostImportantError", () => {
  it("shows nothing when all is well", () => {
    expect(mostImportantError({})).toBeUndefined();
  });

  it("explains a lost position by the missing internet", () => {
    expect(mostImportantError({ positionLost: { kind: "positionLost" }, offline: { kind: "offline" } })).toEqual({
      kind: "offline",
    });
  });

  it("puts a crash above everything else", () => {
    expect(
      mostImportantError({
        offline: { kind: "offline" },
        dataUnavailable: { kind: "dataUnavailable" },
        unexpected: { kind: "unexpected" },
      }),
    ).toEqual({ kind: "unexpected" });
  });
});
