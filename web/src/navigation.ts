import type { DeadEnd } from "./liveRide";
import { isValidVehicleNumber } from "./screens/ManualEntryScreen";
import type { RideInfo } from "./types";

export interface Ride {
  vehicle: string;
  line?: string;
}

export type Screen =
  | { name: "start" }
  | { name: "vehicleNumber" }
  | { name: "qrScanner" }
  | { name: "findingVehicle"; ride: Ride }
  | { name: "vehicleFound"; info: RideInfo }
  | { name: "journey"; info: RideInfo }
  | { name: "deadEnd"; problem: DeadEnd; vehicle: string; line?: string };

const LINE = /^[0-9A-Z]{1,4}$/;

export function readRideFromUrl(search: string): Ride | null {
  const params = new URLSearchParams(search);
  const vehicle = params.get("vehicle")?.trim() ?? "";
  if (!isValidVehicleNumber(vehicle)) return null;
  const line = params.get("line")?.trim().toUpperCase() ?? "";
  return LINE.test(line) ? { vehicle, line } : { vehicle };
}

export function readRideFromQrCode(text: string): Ride | null {
  if (!URL.canParse(text)) return null;
  return readRideFromUrl(new URL(text).search);
}

export function screenFromUrl(search: string): Screen {
  const ride = readRideFromUrl(search);
  return ride ? { name: "findingVehicle", ride } : { name: "start" };
}
