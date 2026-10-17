import { useEffect, useRef, useState } from "react";
import { fetchRide, RideRequestError, type RideProblem } from "./api";
import { PLACEHOLDER_STORY } from "./data/placeholderRide";
import { useAppErrors } from "./ErrorStatus";
import type { Ride } from "./navigation";
import { FindingVehicleScreen } from "./screens/FindingVehicleScreen";
import { JourneyScreen } from "./screens/JourneyScreen";
import { VehicleFoundScreen } from "./screens/VehicleFoundScreen";
import type { RideInfo } from "./types";

export const REFRESH_MS = 10_000;

export type DeadEnd = Extract<RideProblem, "vehicleNotFound" | "noRoute">;

interface FindVehicleProps {
  ride: Ride;
  onFound: (info: RideInfo) => void;
  onDeadEnd: (problem: DeadEnd, line?: string) => void;
  onCancel: () => void;
}

export function FindVehicle({ ride, onFound, onDeadEnd, onCancel }: FindVehicleProps) {
  const { report, resolve } = useAppErrors();
  const handlers = useRef({ onFound, onDeadEnd });
  useEffect(() => {
    handlers.current = { onFound, onDeadEnd };
  });

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    const attempt = async () => {
      try {
        const info = await fetchRide(ride.vehicle, controller.signal);
        resolve("dataUnavailable");
        resolve("positionLost");
        handlers.current.onFound(info);
      } catch (error) {
        if (controller.signal.aborted) return;
        const problem = error instanceof RideRequestError ? error.problem : "unavailable";
        if (problem === "vehicleNotFound" || problem === "noRoute") {
          const line = error instanceof RideRequestError ? error.line : undefined;
          handlers.current.onDeadEnd(problem, line ?? ride.line);
          return;
        }
        report(problem === "noLiveData" ? { kind: "positionLost", line: ride.line } : { kind: "dataUnavailable" });
        timer = window.setTimeout(attempt, REFRESH_MS);
      }
    };
    void attempt();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [ride.vehicle, ride.line, report, resolve]);

  return <FindingVehicleScreen ride={ride} onCancel={onCancel} />;
}

export function useLiveRide(initial: RideInfo): RideInfo {
  const [info, setInfo] = useState(initial);
  const { report, resolve } = useAppErrors();
  const vehicle = initial.vehicle;
  const line = initial.line;

  useEffect(() => {
    const controller = new AbortController();
    let timer: number | undefined;
    const refresh = async () => {
      try {
        setInfo(await fetchRide(vehicle, controller.signal));
        resolve("positionLost");
        resolve("dataUnavailable");
      } catch {
        if (controller.signal.aborted) return;
        report({ kind: "positionLost", line });
      }
      timer = window.setTimeout(refresh, REFRESH_MS);
    };
    timer = window.setTimeout(refresh, REFRESH_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
      resolve("positionLost");
    };
  }, [vehicle, line, report, resolve]);

  return info;
}

export function LiveVehicleFound({ info, onStart }: { info: RideInfo; onStart: (latest: RideInfo) => void }) {
  const live = useLiveRide(info);
  return <VehicleFoundScreen ride={live} onStart={() => onStart(live)} />;
}

export function LiveJourney({ info, onClose }: { info: RideInfo; onClose: () => void }) {
  const live = useLiveRide(info);
  return <JourneyScreen ride={live} story={PLACEHOLDER_STORY} onClose={onClose} />;
}
