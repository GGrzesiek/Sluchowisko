import { Component, createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, ErrorBanner } from "./components";
import { mostImportantError, type ActiveErrors, type AppError, type AppErrorKind } from "./errors";

export const BANNER_VISIBLE_MS = 3000;

interface ErrorActions {
  report: (error: AppError) => void;
  resolve: (kind: AppErrorKind) => void;
}

const ErrorActionsContext = createContext<ErrorActions | null>(null);

export function useAppErrors(): ErrorActions {
  const actions = useContext(ErrorActionsContext);
  if (!actions) throw new Error("useAppErrors needs ErrorStatusProvider");
  return actions;
}

const bannerKey = (error: AppError) => JSON.stringify(error);

export function ErrorStatusProvider({ children }: { children: ReactNode }) {
  const [errors, setErrors] = useState<ActiveErrors>(() => (navigator.onLine ? {} : { offline: { kind: "offline" } }));
  const [seen, setSeen] = useState<Partial<Record<AppErrorKind, string>>>({});

  const actions = useMemo<ErrorActions>(
    () => ({
      report: (error) => setErrors((current) => ({ ...current, [error.kind]: error })),
      resolve: (kind) => {
        setErrors((current) => {
          if (!current[kind]) return current;
          const next = { ...current };
          delete next[kind];
          return next;
        });
        setSeen((current) => {
          if (!current[kind]) return current;
          const next = { ...current };
          delete next[kind];
          return next;
        });
      },
    }),
    [],
  );

  useEffect(() => {
    const goOffline = () => actions.report({ kind: "offline" });
    const goOnline = () => actions.resolve("offline");
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => {
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("online", goOnline);
    };
  }, [actions]);

  const shown = mostImportantError(errors);
  const key = shown && bannerKey(shown);
  const visible = shown !== undefined && (shown.kind === "unexpected" || seen[shown.kind] !== key);

  useEffect(() => {
    if (!shown || !key || !visible || shown.kind === "unexpected") return;
    const timer = setTimeout(() => setSeen((current) => ({ ...current, [shown.kind]: key })), BANNER_VISIBLE_MS);
    return () => clearTimeout(timer);
  }, [shown, key, visible]);

  return (
    <ErrorActionsContext.Provider value={actions}>
      <div className="flex min-h-dvh flex-col">
        {visible && shown && (
          <div className="pointer-events-none fixed inset-x-0 top-0 z-30">
            <div className="animate-fade-in mx-auto max-w-[430px] px-4 pt-[calc(16px+env(safe-area-inset-top))] drop-shadow-lg">
              <ErrorBanner error={shown} />
            </div>
          </div>
        )}
        <div className="flex grow flex-col *:min-h-0 *:w-full *:grow">
          <CrashBoundary>{children}</CrashBoundary>
        </div>
      </div>
    </ErrorActionsContext.Provider>
  );
}

class CrashBoundary extends Component<{ children: ReactNode }, { crashed: boolean }> {
  static contextType = ErrorActionsContext;
  declare context: ErrorActions | null;
  state = { crashed: false };

  static getDerivedStateFromError() {
    return { crashed: true };
  }

  componentDidCatch() {
    this.context?.report({ kind: "unexpected" });
  }

  render() {
    if (!this.state.crashed) return this.props.children;
    return (
      <main className="mx-auto flex w-full max-w-[430px] flex-col justify-end px-6 pb-14">
        <Button onClick={() => window.location.assign(window.location.pathname)}>Zacznij od nowa</Button>
      </main>
    );
  }
}
