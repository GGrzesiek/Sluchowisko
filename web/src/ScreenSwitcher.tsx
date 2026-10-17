import { useState } from "react";
import { App } from "./App";
import { BusAnimation, Button } from "./components";
import { screenFromUrl, type Screen } from "./navigation";
import { PlaceholderScreen } from "./screens/PlaceholderScreen";
import { StartScreen } from "./screens/StartScreen";

export function ScreenSwitcher() {
  if (window.location.hash === "#components") return <App />;
  return <CurrentScreen />;
}

function CurrentScreen() {
  const [screen, setScreen] = useState<Screen>(() => screenFromUrl(window.location.search));

  const goTo = (next: Screen) => {
    if (next.name === "start" && window.location.search) {
      window.history.replaceState(null, "", window.location.pathname);
    }
    setScreen(next);
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
      return <PlaceholderScreen title="Którym autobusem lub tramwajem jedziesz?" onBack={goToStart} />;
    case "qrScanner":
      return <PlaceholderScreen title="Skanowanie kodu QR" onBack={goToStart} />;
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
