import { readRideFromQrCode, readRideFromUrl, screenFromUrl } from "./navigation";

describe("readRideFromUrl", () => {
  it("reads line and vehicle from a QR sticker link", () => {
    expect(readRideFromUrl("?line=180&vehicle=1234")).toEqual({ line: "180", vehicle: "1234" });
  });

  it("keeps a night line and normalises its case", () => {
    expect(readRideFromUrl("?line=n12&vehicle=1234")).toEqual({ line: "N12", vehicle: "1234" });
  });

  it("accepts a vehicle without a line", () => {
    expect(readRideFromUrl("?vehicle=1234")).toEqual({ vehicle: "1234" });
  });

  it("drops a malformed line but keeps the vehicle", () => {
    expect(readRideFromUrl("?line=<b>&vehicle=1234")).toEqual({ vehicle: "1234" });
  });

  it("rejects a missing or malformed vehicle", () => {
    expect(readRideFromUrl("")).toBeNull();
    expect(readRideFromUrl("?line=180")).toBeNull();
    expect(readRideFromUrl("?line=180&vehicle=abc")).toBeNull();
    expect(readRideFromUrl("?line=180&vehicle=123")).toBeNull();
    expect(readRideFromUrl("?line=180&vehicle=12345")).toBeNull();
  });
});

describe("readRideFromQrCode", () => {
  it("reads the ride from a sticker link", () => {
    expect(readRideFromQrCode("https://ggrzesiek.dev/opendatahackathon42/?line=180&vehicle=1234")).toEqual({
      line: "180",
      vehicle: "1234",
    });
  });

  it("ignores codes that are not our sticker links", () => {
    expect(readRideFromQrCode("1234")).toBeNull();
    expect(readRideFromQrCode("https://example.com/menu")).toBeNull();
  });
});

describe("screenFromUrl", () => {
  it("skips the start screen when the link names a vehicle", () => {
    expect(screenFromUrl("?line=180&vehicle=1234")).toEqual({
      name: "findingVehicle",
      ride: { line: "180", vehicle: "1234" },
    });
  });

  it("starts on the start screen otherwise", () => {
    expect(screenFromUrl("?vehicle=")).toEqual({ name: "start" });
  });
});
