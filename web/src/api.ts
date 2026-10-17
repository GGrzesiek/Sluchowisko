import type { RideInfo } from "./types";

export type RideProblem = "vehicleNotFound" | "noRoute" | "noLiveData" | "unavailable";

export class RideRequestError extends Error {
  readonly problem: RideProblem;
  readonly line?: string;

  constructor(problem: RideProblem, line?: string) {
    super(problem);
    this.name = "RideRequestError";
    this.problem = problem;
    this.line = line;
  }
}

const PROBLEMS: Record<string, RideProblem> = {
  vehicle_not_found: "vehicleNotFound",
  no_route: "noRoute",
  no_live_data: "noLiveData",
};

export const API_URL: string = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");

export async function fetchRide(vehicle: string, signal?: AbortSignal): Promise<RideInfo> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/ride/${encodeURIComponent(vehicle)}/stops/`, {
      signal,
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new RideRequestError("unavailable");
  }
  const body: unknown = await response.json().catch(() => null);
  if (response.ok && isRideInfo(body)) return body;
  const details = typeof body === "object" && body !== null ? (body as { code?: unknown; line?: unknown }) : {};
  const problem = typeof details.code === "string" ? PROBLEMS[details.code] : undefined;
  throw new RideRequestError(problem ?? "unavailable", typeof details.line === "string" ? details.line : undefined);
}

function isRideInfo(body: unknown): body is RideInfo {
  if (typeof body !== "object" || body === null) return false;
  const ride = body as Partial<RideInfo>;
  return typeof ride.vehicle === "string" && typeof ride.destination === "string" && Array.isArray(ride.stops);
}
