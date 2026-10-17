import sampleNarration from "../assets/sample-narration.m4a";
import type { RideInfo, StoryContent } from "../types";

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

export const PLACEHOLDER_STORY: StoryContent = {
  title: "Hala Mirowska",
  audio: sampleNarration,
  photos: [
    {
      alt: "Hala Mirowska od strony placu",
      year: "1936",
      caption: "Hala Mirowska · otwarcie",
      credit: "Fot. NN · NAC / Wikimedia Commons · domena publiczna",
    },
    {
      alt: "Targ przed halą",
      year: "1902",
      caption: "Targ przed halą",
      credit: "Fot. NN · Wikimedia Commons · domena publiczna",
    },
    {
      alt: "Hala po odbudowie",
      year: "1951",
      caption: "Hala po odbudowie",
      credit: "Fot. NN · NAC · domena publiczna",
    },
  ],
  body: {
    format: "plain",
    text: "Hale Mirowskie zbudowano na przełomie XIX i XX wieku jako miejski targ.\n\nTo tekst zastępczy. Prawdziwa treść przyjdzie z backendu, jako zwykły tekst w akapitach.\n\nDzisiaj mijasz hale w drodze do pracy.",
  },
  sources: [{ label: "Hale Mirowskie · Wikipedia", href: "https://pl.wikipedia.org/wiki/Hale_Mirowskie" }],
};
