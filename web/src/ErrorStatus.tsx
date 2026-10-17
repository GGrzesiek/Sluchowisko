import { Component, createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Button, ErrorBanner } from "./components";
import { mostImportantError, type ActiveErrors, type AppError, type AppErrorKind } from "./errors";

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

export function ErrorStatusProvider({ children }: { children: ReactNode }) {
  const [errors, setErrors] = useState<ActiveErrors>(() => (navigator.onLine ? {} : { offline: { kind: "offline" } }));

  const actions = useMemo<ErrorActions>(
    () => ({
      report: (error) => setErrors((current) => ({ ...current, [error.kind]: error })),
      resolve: (kind) =>
        setErrors((current) => {
          if (!current[kind]) return current;
          const next = { ...current };
          delete next[kind];
          return next;
        }),
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

  return (
    <ErrorActionsContext.Provider value={actions}>
      <div className="flex min-h-dvh flex-col">
        {shown && (
          <div className="sticky top-0 z-10 bg-paper">
            <div className="mx-auto max-w-[430px] px-4 pt-[calc(16px+env(safe-area-inset-top))] pb-2">
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
      <main className="mx-auto flex w-full max-w-[430px] flex-col px-6 pt-6">
        <Button onClick={() => window.location.assign(window.location.pathname)}>Zacznij od nowa</Button>
      </main>
    );
  }
}
