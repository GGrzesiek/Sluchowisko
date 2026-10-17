import { rideSocketUrl, type RideProblem } from "./api";
import type { RideInfo, StoryContent } from "./types";

export const PING_MS = 20_000;
export const PONG_TIMEOUT_MS = 10_000;
export const RECONNECT_MIN_MS = 1_000;
export const RECONNECT_MAX_MS = 10_000;
const CLOSE_UNKNOWN_VEHICLE = 4404;

export interface LocationInfo {
  groupId: string;
  story: StoryContent | null;
}

export interface RideSocketHandlers {
  onRoute: (info: RideInfo) => void;
  onLocation?: (info: LocationInfo) => void;
  onProblem: (problem: RideProblem, line?: string) => void;
  onDisconnect: () => void;
}

const PROBLEMS: Record<string, RideProblem> = {
  vehicle_not_found: "vehicleNotFound",
  no_route: "noRoute",
  no_live_data: "noLiveData",
};

function isRideInfo(body: unknown): body is RideInfo {
  if (typeof body !== "object" || body === null) return false;
  const ride = body as Partial<RideInfo>;
  return typeof ride.vehicle === "string" && typeof ride.destination === "string" && Array.isArray(ride.stops);
}

export function openRideSocket(vehicle: string, handlers: RideSocketHandlers): () => void {
  let socket: WebSocket | undefined;
  let reconnectTimer: number | undefined;
  let pingTimer: number | undefined;
  let pongTimer: number | undefined;
  let attempt = 0;
  let closed = false;

  const stopHeartbeat = () => {
    window.clearInterval(pingTimer);
    window.clearTimeout(pongTimer);
  };

  const handleMessage = (raw: unknown) => {
    window.clearTimeout(pongTimer);
    if (typeof raw !== "string") return;
    let message: { type?: unknown; data?: unknown };
    try {
      message = JSON.parse(raw);
    } catch {
      return;
    }
    if (message.type === "route" && isRideInfo(message.data)) {
      handlers.onRoute(message.data);
    } else if (message.type === "location" && handlers.onLocation) {
      handlers.onLocation(message.data as LocationInfo);
    } else if (message.type === "error") {
      const details = (message.data ?? {}) as { code?: unknown; line?: unknown };
      const code = typeof details.code === "string" ? details.code : "";
      handlers.onProblem(PROBLEMS[code] ?? "unavailable", typeof details.line === "string" ? details.line : undefined);
    }
  };

  const connect = () => {
    const ws = new WebSocket(rideSocketUrl(vehicle));
    socket = ws;
    ws.onopen = () => {
      attempt = 0;
      pingTimer = window.setInterval(() => {
        try {
          ws.send(JSON.stringify({ type: "ping" }));
        } catch {
          ws.close();
          return;
        }
        pongTimer = window.setTimeout(() => ws.close(), PONG_TIMEOUT_MS);
      }, PING_MS);
    };
    ws.onmessage = (event) => handleMessage(event.data);
    ws.onerror = () => {};
    ws.onclose = (event) => {
      stopHeartbeat();
      if (closed || socket !== ws) return;
      handlers.onDisconnect();
      if (event.code === CLOSE_UNKNOWN_VEHICLE) return;
      const delay = Math.min(RECONNECT_MIN_MS * 2 ** attempt, RECONNECT_MAX_MS);
      attempt += 1;
      reconnectTimer = window.setTimeout(connect, delay);
    };
  };

  connect();

  return () => {
    closed = true;
    stopHeartbeat();
    window.clearTimeout(reconnectTimer);
    socket?.close();
  };
}
