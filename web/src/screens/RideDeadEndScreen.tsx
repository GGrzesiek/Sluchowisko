import { Button, LineBadge, LineChip } from "../components";

const LINES_WITH_STORIES = ["4", "161", "N50"];

interface RideDeadEndScreenProps {
  problem: "vehicleNotFound" | "noRoute";
  vehicle: string;
  line?: string;
  onEnterAnother: () => void;
  onStart: () => void;
}

export function RideDeadEndScreen({ problem, vehicle, line, onEnterAnother, onStart }: RideDeadEndScreenProps) {
  const notFound = problem === "vehicleNotFound";
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col bg-paper px-6 pt-10 pb-14 text-charcoal">
      <section className="flex grow flex-col items-center justify-center gap-5 py-8 text-center">
        {notFound ? (
          <span
            role="img"
            aria-label={`Pojazd ${vehicle}`}
            className="font-condensed inline-flex h-16 min-w-28 items-center justify-center rounded-[14px] border-2 border-dashed border-umber px-4 text-[44px] font-black tracking-[0.04em] text-umber"
          >
            {vehicle}
          </span>
        ) : (
          line && <LineBadge line={line} kind="plain" size="md" label={`Linia ${line}`} />
        )}
        <h1 className="m-0 max-w-[320px] text-[28px] font-extrabold leading-[1.15] tracking-[-0.02em] text-balance">
          {notFound ? "Nie widzimy tego pojazdu" : "Nie mamy jeszcze historii dla tej linii"}
        </h1>
        {notFound ? (
          <p className="m-0 max-w-[300px] text-base leading-[1.45] text-umber">
            Sprawdź numer nad przednią albo tylną szybą. Pojazd musi być teraz w trasie.
          </p>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <p className="m-0 text-base leading-[1.45] text-umber">Historie mamy na liniach:</p>
            <ul
              aria-label="Linie z historiami"
              className="m-0 flex list-none flex-wrap justify-center gap-2 p-0 text-2xl"
            >
              {LINES_WITH_STORIES.map((storyLine) => (
                <li key={storyLine}>
                  <LineChip line={storyLine} tone="bus" />
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
      <div className="flex flex-col gap-3">
        <Button onClick={onEnterAnother}>Wpisz inny numer</Button>
        <Button variant="outline" onClick={onStart}>
          Wróć na początek
        </Button>
      </div>
    </main>
  );
}
