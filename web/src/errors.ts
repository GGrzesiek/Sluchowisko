export type AppError =
  | { kind: "unexpected" }
  | { kind: "offline" }
  | { kind: "dataUnavailable" }
  | { kind: "positionLost"; line?: string; lastStop?: string };

export type AppErrorKind = AppError["kind"];

export const ERROR_PRIORITY: AppErrorKind[] = ["unexpected", "offline", "dataUnavailable", "positionLost"];

export const ERROR_MESSAGES: Record<AppErrorKind, { title: string; detail: string }> = {
  unexpected: { title: "Coś poszło nie tak", detail: "Zacznij od nowa, żeby spróbować jeszcze raz." },
  offline: { title: "Brak internetu", detail: "Poczekaj, aż telefon złapie sieć." },
  dataUnavailable: { title: "Nie udało się wczytać danych", detail: "Odśwież stronę, żeby spróbować jeszcze raz." },
  positionLost: { title: "Łączymy ponownie…", detail: "Historia gra dalej. Przystanki mogą się chwilę spóźniać." },
};

export type ActiveErrors = Partial<Record<AppErrorKind, AppError>>;

export function mostImportantError(errors: ActiveErrors): AppError | undefined {
  const kind = ERROR_PRIORITY.find((k) => errors[k]);
  return kind && errors[kind];
}
