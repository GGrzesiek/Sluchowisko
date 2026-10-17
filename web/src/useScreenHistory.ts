import { useCallback, useEffect, useState } from "react";
import { flushSync } from "react-dom";
import { screenFromUrl, type Screen } from "./navigation";

interface HistoryEntry {
  index: number;
  screen: Screen;
}

export interface Navigator {
  screen: Screen;
  goTo: (next: Screen, options?: { replace?: boolean }) => void;
  goBack: () => void;
}

function readEntry(state: unknown): HistoryEntry | null {
  if (typeof state !== "object" || state === null) return null;
  const entry = state as Partial<HistoryEntry>;
  const screen = entry.screen as Partial<Screen> | undefined;
  return typeof entry.index === "number" && typeof screen?.name === "string" ? (entry as HistoryEntry) : null;
}

function currentIndex(): number {
  return readEntry(window.history.state)?.index ?? 0;
}

export function useScreenHistory(): Navigator {
  const [screen, setScreen] = useState<Screen>(
    () => readEntry(window.history.state)?.screen ?? screenFromUrl(window.location.search),
  );

  useEffect(() => {
    if (!readEntry(window.history.state)) {
      window.history.replaceState({ index: 0, screen } satisfies HistoryEntry, "");
    }
    const onPopState = (event: PopStateEvent) => {
      setScreen(readEntry(event.state)?.screen ?? screenFromUrl(window.location.search));
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const goTo = useCallback((next: Screen, options?: { replace?: boolean }) => {
    const index = options?.replace ? currentIndex() : currentIndex() + 1;
    const url = next.name === "start" ? window.location.pathname : window.location.href;
    const entry: HistoryEntry = { index, screen: next };
    if (options?.replace) window.history.replaceState(entry, "", url);
    else window.history.pushState(entry, "", url);
    flushSync(() => setScreen(next));
  }, []);

  const goBack = useCallback(() => {
    if (currentIndex() > 0) window.history.back();
    else goTo({ name: "start" }, { replace: true });
  }, [goTo]);

  return { screen, goTo, goBack };
}
