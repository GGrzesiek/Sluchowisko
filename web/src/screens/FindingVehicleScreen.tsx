import { BusAnimation, Button, VehicleTag } from "../components";
import type { Ride } from "../navigation";

export function FindingVehicleScreen({ ride, onCancel }: { ride: Ride; onCancel: () => void }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col bg-paper px-6 pt-5 pb-[calc(56px+env(safe-area-inset-bottom))] text-charcoal">
      <div className="flex h-12 items-center gap-3">
        <VehicleTag number={ride.vehicle} />
        {ride.line && <span className="text-[17px] font-extrabold">Linia {ride.line}</span>}
      </div>
      <div className="flex grow flex-col justify-center gap-5">
        <BusAnimation className="-mx-6" />
        <div role="status" className="flex flex-col items-center gap-2.5 text-center">
          <h1 className="m-0 text-[28px] font-extrabold tracking-[-0.02em]">Szukamy Twojego autobusu…</h1>
          <p className="m-0 max-w-[300px] text-base leading-[1.4] text-umber">
            Łączymy pojazd {ride.vehicle} z danymi o komunikacji miejskiej na żywo
          </p>
        </div>
      </div>
      <Button variant="outline" onClick={onCancel}>
        Anuluj
      </Button>
    </main>
  );
}
