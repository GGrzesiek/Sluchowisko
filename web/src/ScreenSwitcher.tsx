import { useState } from "react";
import { flushSync } from "react-dom";
import { App } from "./App";
import { BusAnimation, Button } from "./components";
import { screenFromUrl, type Screen } from "./navigation";
import { ManualEntryScreen } from "./screens/ManualEntryScreen";
import { PlaceholderScreen } from "./screens/PlaceholderScreen";
import { QrScannerScreen } from "./screens/QrScannerScreen";
import { StartScreen } from "./screens/StartScreen";

export function ScreenSwitcher() {
  const hash = window.location.hash;
  if (hash === "#components" || hash.startsWith("#/")) return <App />;
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
        <PlaceholderScreen title="Szukamy Twojego autobusu…">
          <BusAnimation className="-mx-6" />
          <p className="m-0 text-base text-umber">
            Pojazd {screen.ride.vehicle}
            {screen.ride.line && `, linia ${screen.ride.line}`}
          </p>
          <Button variant="outline" onClick={goToStart}>
            Anuluj
          </Button>
        </PlaceholderScreen>
      );
  }
}
