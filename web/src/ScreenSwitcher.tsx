import { useState } from "react";
import { flushSync } from "react-dom";
import { App } from "./App";
import { FindVehicle, LiveJourney, LiveVehicleFound } from "./liveRide";
import { screenFromUrl, type Screen } from "./navigation";
import { ManualEntryScreen } from "./screens/ManualEntryScreen";
import { QrScannerScreen } from "./screens/QrScannerScreen";
import { RideDeadEndScreen } from "./screens/RideDeadEndScreen";
import { StartScreen } from "./screens/StartScreen";

export function isDebugPath(pathname: string): boolean {
  return pathname.replace(/\/+$/, "").endsWith("/debug");
}

export function ScreenSwitcher() {
  const hash = window.location.hash;
  if (isDebugPath(window.location.pathname) || hash === "#components" || hash.startsWith("#/")) return <App />;
  return <CurrentScreen />;
}

function CurrentScreen() {
  const [screen, setScreen] = useState<Screen>(() => screenFromUrl(window.location.search));

  const goTo = (next: Screen) => {
    if (next.name === "start" && window.location.search) {
      window.history.replaceState(null, "", window.location.pathname);
    }
    flushSync(() => setScreen(next));
  };
  const goToStart = () => goTo({ name: "start" });

  switch (screen.name) {
    case "start":
      return (
        <StartScreen
          onEnterVehicleNumber={() => goTo({ name: "vehicleNumber" })}
          onScanQr={() => goTo({ name: "qrScanner" })}
        />
      );
    case "vehicleNumber":
      return (
        <ManualEntryScreen
          onBack={goToStart}
          onSubmit={(vehicle) => goTo({ name: "findingVehicle", ride: { vehicle } })}
        />
      );
    case "qrScanner":
      return (
        <QrScannerScreen
          onBack={goToStart}
          onRideFound={(ride) => goTo({ name: "findingVehicle", ride })}
          onEnterVehicleNumber={() => goTo({ name: "vehicleNumber" })}
        />
      );
    case "findingVehicle":
      return (
        <FindVehicle
          ride={screen.ride}
          onFound={(info) => goTo({ name: "vehicleFound", info })}
          onDeadEnd={(problem, line) => goTo({ name: "deadEnd", problem, vehicle: screen.ride.vehicle, line })}
          onCancel={goToStart}
        />
      );
    case "vehicleFound":
      return <LiveVehicleFound info={screen.info} onStart={(info) => goTo({ name: "journey", info })} />;
    case "journey":
      return <LiveJourney info={screen.info} onClose={goToStart} />;
    case "deadEnd":
      return (
        <RideDeadEndScreen
          problem={screen.problem}
          vehicle={screen.vehicle}
          line={screen.line}
          onEnterAnother={() => goTo({ name: "vehicleNumber" })}
          onStart={goToStart}
        />
      );
  }
}
