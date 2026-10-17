import { createContext, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import type { StoryContent } from "./types";

interface NarrationState {
  src?: string;
  playing: boolean;
  elapsed: number;
  duration: number;
}

interface NarrationActions {
  start: (story: StoryContent) => void;
  toggle: (story: StoryContent) => void;
  stop: () => void;
}

export type Narration = NarrationState & NarrationActions;

const IDLE: NarrationState = { playing: false, elapsed: 0, duration: 0 };

const NarrationContext = createContext<Narration | null>(null);

export function useNarration(): Narration {
  const narration = useContext(NarrationContext);
  if (!narration) throw new Error("useNarration needs NarrationProvider");
  return narration;
}

export function clock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "--:--";
  const whole = Math.floor(seconds);
  return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

export function NarrationProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement>(null);
  const current = useRef<string | undefined>(undefined);
  const [state, setState] = useState<NarrationState>(IDLE);

  const actions = useMemo<NarrationActions>(() => {
    const play = () => {
      const element = audio.current;
      if (!element) return;
      Promise.resolve(element.play()).catch(() => setState((now) => ({ ...now, playing: false })));
    };
    const pause = () => audio.current?.pause();
    const start = (story: StoryContent) => {
      const element = audio.current;
      if (!element || !story.audio) return;
      if (current.current === story.audio) element.currentTime = 0;
      else element.src = story.audio;
      current.current = story.audio;
      setState({ ...IDLE, src: story.audio });
      showOnLockScreen(story.title, play, pause);
      play();
    };

    return {
      start,
      toggle(story) {
        const element = audio.current;
        if (!element || !story.audio) return;
        if (current.current !== story.audio) start(story);
        else if (element.paused) play();
        else pause();
      },
      stop() {
        const element = audio.current;
        if (!element) return;
        element.pause();
        element.removeAttribute("src");
        element.load();
        current.current = undefined;
        setState(IDLE);
      },
    };
  }, []);

  const value = useMemo(() => ({ ...state, ...actions }), [state, actions]);
  const update = (change: Partial<NarrationState>) => setState((now) => ({ ...now, ...change }));

  return (
    <NarrationContext.Provider value={value}>
      {children}
      <audio
        ref={audio}
        preload="auto"
        className="hidden"
        onPlay={() => update({ playing: true })}
        onPause={() => update({ playing: false })}
        onEnded={(event) => update({ playing: false, elapsed: event.currentTarget.duration })}
        onError={() => update({ playing: false })}
        onTimeUpdate={(event) => update({ elapsed: event.currentTarget.currentTime })}
        onDurationChange={(event) => update({ duration: event.currentTarget.duration })}
      />
    </NarrationContext.Provider>
  );
}

function showOnLockScreen(title: string, play: () => void, pause: () => void) {
  if (!("mediaSession" in navigator) || typeof MediaMetadata === "undefined") return;
  navigator.mediaSession.metadata = new MediaMetadata({ title, artist: "Słuchowisko" });
  navigator.mediaSession.setActionHandler("play", play);
  navigator.mediaSession.setActionHandler("pause", pause);
}
