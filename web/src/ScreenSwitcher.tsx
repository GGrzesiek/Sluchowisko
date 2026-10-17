import { App } from "./App";
import { FindVehicle, LiveJourney, LiveVehicleFound } from "./liveRide";
import { ManualEntryScreen } from "./screens/ManualEntryScreen";
import { QrScannerScreen } from "./screens/QrScannerScreen";
import { RideDeadEndScreen } from "./screens/RideDeadEndScreen";
import { StartScreen } from "./screens/StartScreen";
import { useScreenHistory } from "./useScreenHistory";

export function isDebugPath(pathname: string): boolean {
  return pathname.replace(/\/+$/, "").endsWith("/debug");
}

export function ScreenSwitcher() {
  const hash = window.location.hash;
  if (isDebugPath(window.location.pathname) || hash === "#components" || hash.startsWith("#/")) return <App />;
  return <CurrentScreen />;
}

function CurrentScreen() {
  const { screen, goTo, goBack } = useScreenHistory();
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
          onBack={goBack}
          onSubmit={(vehicle) => goTo({ name: "findingVehicle", ride: { vehicle } })}
        />
      );
    case "qrScanner":
      return (
        <QrScannerScreen
          onBack={goBack}
          onRideFound={(ride) => goTo({ name: "findingVehicle", ride })}
          onEnterVehicleNumber={() => goTo({ name: "vehicleNumber" })}
        />
      );
    case "findingVehicle":
      return (
        <FindVehicle
          ride={screen.ride}
          onFound={(info) => goTo({ name: "vehicleFound", info }, { replace: true })}
          onDeadEnd={(problem, line) =>
            goTo({ name: "deadEnd", problem, vehicle: screen.ride.vehicle, line }, { replace: true })
          }
          onCancel={goBack}
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
