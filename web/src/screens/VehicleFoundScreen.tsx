import { Button, RouteStrip, VehicleHeader } from "../components";
import type { RideInfo } from "../types";

interface VehicleFoundScreenProps {
  ride: RideInfo;
  onStart: () => void;
}

export function VehicleFoundScreen({ ride, onStart }: VehicleFoundScreenProps) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col bg-paper px-6 pb-14 pt-5">
      <VehicleHeader vehicle={ride.vehicle} destination={ride.destination} />
      <RouteStrip stops={ride.stops} height={300} axisY={210} showLegend className="mt-[124px]" />
      <Button onClick={onStart} className="mt-auto">
        Zaczynamy
      </Button>
    </main>
  );
}
