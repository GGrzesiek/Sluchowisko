import type { RideInfo } from "../types";

export const PLACEHOLDER_RIDE: RideInfo = {
  vehicle: "1234",
  destination: "Dworzec Wileński",
  stops: [
    { name: "Dworzec Zachodni", state: "passed" },
    { name: "Rondo Daszyńskiego", state: "passed" },
    { name: "Rondo ONZ", state: "passed" },
    { name: "Pl. Defilad", state: "passed" },
    { name: "Hala Mirowska", state: "passed", hasStory: true },
    { name: "Centrum", state: "passed" },
    { name: "Krucza", state: "passed" },
    { name: "Muzeum Narodowe", state: "passed" },
    { name: "Most Poniatowskiego", state: "current", hasStory: true },
    { name: "Rondo Waszyngtona", state: "next", etaMinutes: 2 },
    { name: "Berezyńska", state: "next", etaMinutes: 4 },
    { name: "Dw. Wschodni", state: "next", etaMinutes: 6, hasStory: true },
    { name: "Targowa", state: "upcoming", etaMinutes: 9 },
    { name: "Dworzec Wileński", state: "upcoming", etaMinutes: 12 },
  ],
};
