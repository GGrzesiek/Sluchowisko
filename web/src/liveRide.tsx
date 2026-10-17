import { useEffect, useRef, useState } from "react";
import type { RideProblem } from "./api";
import { PLACEHOLDER_STORY } from "./data/placeholderRide";
import { useAppErrors } from "./ErrorStatus";
import { useNarration } from "./Narration";
import type { Ride } from "./navigation";
import { openRideSocket } from "./rideSocket";
import { FindingVehicleScreen } from "./screens/FindingVehicleScreen";
import { JourneyScreen } from "./screens/JourneyScreen";
import { VehicleFoundScreen } from "./screens/VehicleFoundScreen";
import type { RideInfo } from "./types";

export type DeadEnd = Extract<RideProblem, "vehicleNotFound" | "noRoute">;

export const MIN_LOADING_MS = 1200;

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
    const shownAt = Date.now();
    let pending: ReturnType<typeof setTimeout> | undefined;
    const afterLoading = (next: () => void) => {
      clearTimeout(pending);
      pending = setTimeout(next, Math.max(0, MIN_LOADING_MS - (Date.now() - shownAt)));
    };
    const close = openRideSocket(ride.vehicle, {
      onRoute: (info) => {
        resolve("dataUnavailable");
        resolve("positionLost");
        afterLoading(() => handlers.current.onFound(info));
      },
      onProblem: (problem, line) => {
        if (problem === "vehicleNotFound" || problem === "noRoute") {
          afterLoading(() => handlers.current.onDeadEnd(problem, line ?? ride.line));
        } else {
          report(problem === "noLiveData" ? { kind: "positionLost", line: ride.line } : { kind: "dataUnavailable" });
        }
      },
      onDisconnect: () => report({ kind: "dataUnavailable" }),
    });
    return () => {
      clearTimeout(pending);
      close();
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
    const lost = () => report({ kind: "positionLost", line });
    const close = openRideSocket(vehicle, {
      onRoute: (next) => {
        setInfo(next);
        resolve("positionLost");
        resolve("dataUnavailable");
      },
      onProblem: lost,
      onDisconnect: lost,
    });
    return () => {
      close();
      resolve("positionLost");
    };
  }, [vehicle, line, report, resolve]);

  return info;
}

export function LiveVehicleFound({ info, onStart }: { info: RideInfo; onStart: (latest: RideInfo) => void }) {
  const live = useLiveRide(info);
  const narration = useNarration();
  const start = () => {
    narration.start(PLACEHOLDER_STORY);
    onStart(live);
  };
  return <VehicleFoundScreen ride={live} onStart={start} />;
}

export function LiveJourney({ info, onClose }: { info: RideInfo; onClose: () => void }) {
  const live = useLiveRide(info);
  const narration = useNarration();
  const close = () => {
    narration.stop();
    onClose();
  };
  return <JourneyScreen ride={live} story={PLACEHOLDER_STORY} onClose={close} />;
}
