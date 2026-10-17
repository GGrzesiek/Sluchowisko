export type RideProblem = "vehicleNotFound" | "noRoute" | "noLiveData" | "unavailable";

export const API_URL: string = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");

export function rideSocketUrl(vehicle: string): string {
  const base = API_URL
    ? API_URL.replace(/^http/, "ws")
    : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  return `${base}/ws/ride/${encodeURIComponent(vehicle)}/`;
}
