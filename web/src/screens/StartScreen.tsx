import { BusAnimation, Button, UiIcon } from "../components";

export function StartScreen({
  onEnterVehicleNumber,
  onScanQr,
}: {
  onEnterVehicleNumber: () => void;
  onScanQr: () => void;
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col bg-paper px-6 pb-[calc(56px+env(safe-area-inset-bottom))] text-charcoal">
      <h1 className="sr-only">Muzeum w autobusie</h1>
      <div className="flex grow items-center">
        <BusAnimation className="-mx-6 grow" />
      </div>
      <div className="flex gap-4">
        <Button
          variant="outline"
          aria-label="Wpisz numer boczny pojazdu"
          className="grow"
          onClick={onEnterVehicleNumber}
        >
          Nr boczny
        </Button>
        <Button aria-label="Zeskanuj kod QR" className="w-[108px] shrink-0" onClick={onScanQr}>
          <UiIcon name="qr" size={38} strokeWidth={1.6} />
        </Button>
      </div>
    </main>
  );
}
