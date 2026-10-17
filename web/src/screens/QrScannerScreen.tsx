import QrScanner from "qr-scanner";
import { useEffect, useRef, useState } from "react";
import { BackBar, Button } from "../components";
import { readRideFromQrCode, type Ride } from "../navigation";

type Problem = "noCamera" | "notOurCode";

const MESSAGES: Record<Problem | "aim", string> = {
  aim: "Nakieruj aparat na kod QR z naklejki w pojeździe.",
  notOurCode: "To nie jest kod z naszej naklejki. Spróbuj jeszcze raz.",
  noCamera: "Nie mamy dostępu do aparatu. Zezwól na niego w ustawieniach przeglądarki albo wpisz numer taborowy.",
};

export function QrScannerScreen({
  onBack,
  onRideFound,
  onEnterVehicleNumber,
}: {
  onBack: () => void;
  onRideFound: (ride: Ride) => void;
  onEnterVehicleNumber: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [problem, setProblem] = useState<Problem>();

  useEffect(() => {
    const scanner = new QrScanner(
      video.current!,
      (result) => {
        const ride = readRideFromQrCode(result.data);
        if (!ride) return setProblem("notOurCode");
        scanner.stop();
        onRideFound(ride);
      },
      { preferredCamera: "environment", maxScansPerSecond: 5, returnDetailedScanResult: true },
    );
    scanner.start().catch(() => setProblem("noCamera"));
    return () => scanner.destroy();
  }, [onRideFound]);

  return (
    <main className="relative mx-auto flex min-h-dvh max-w-md flex-col gap-6 overflow-hidden bg-ink-deep px-6 pt-5 pb-[calc(56px+env(safe-area-inset-bottom))] text-cream">
      <video ref={video} muted playsInline aria-hidden="true" className="absolute inset-0 h-full w-full object-cover" />
      <div className="relative">
        <BackBar onBack={onBack} />
      </div>
      <h1 className="relative m-0 text-[28px] font-extrabold leading-tight tracking-[-0.02em]">
        Zeskanuj kod z naklejki
      </h1>
      <div className="relative flex grow items-center justify-center">
        {problem !== "noCamera" && (
          <div aria-hidden="true" className="aspect-square w-full max-w-[280px] rounded-3xl border-4 border-cream/90" />
        )}
      </div>
      <p role="status" className="relative m-0 rounded-2xl bg-ink-deep/80 p-4 text-base font-semibold leading-snug">
        {MESSAGES[problem ?? "aim"]}
      </p>
      {problem === "noCamera" && (
        <Button className="relative" onClick={onEnterVehicleNumber}>
          Wpisz numer taborowy
        </Button>
      )}
    </main>
  );
}
