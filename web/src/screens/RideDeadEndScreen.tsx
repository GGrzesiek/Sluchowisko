import { Button } from "../components";

const DEMO_LINES = "22, 18, 179, 169 i 117";

interface RideDeadEndScreenProps {
  problem: "vehicleNotFound" | "noRoute";
  vehicle: string;
  line?: string;
  onEnterAnother: () => void;
  onStart: () => void;
}

export function RideDeadEndScreen({ problem, vehicle, line, onEnterAnother, onStart }: RideDeadEndScreenProps) {
  const title =
    problem === "vehicleNotFound"
      ? `Nie widzimy pojazdu ${vehicle}`
      : `Nie mamy jeszcze historii dla linii${line ? ` ${line}` : ""}.`;
  const detail =
    problem === "vehicleNotFound"
      ? "Sprawdź numer nad drzwiami albo przy kabinie kierowcy. Pojazd musi być teraz w trasie."
      : `Historie są na liniach ${DEMO_LINES}.`;
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col gap-4 bg-paper px-6 pt-10 pb-14 text-charcoal">
      <h1 className="m-0 text-[26px] font-extrabold leading-[1.15] tracking-[-0.02em]">{title}</h1>
      <p className="m-0 text-base leading-[1.4] text-umber">{detail}</p>
      <div className="mt-auto flex flex-col gap-3">
        <Button onClick={onEnterAnother}>Wpisz inny numer</Button>
        <Button variant="outline" onClick={onStart}>
          Wróć na początek
        </Button>
      </div>
    </main>
  );
}
