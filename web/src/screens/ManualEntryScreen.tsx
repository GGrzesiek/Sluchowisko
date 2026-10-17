import { useState, type FormEvent } from "react";
import { BackBar, Button, UiIcon, VehicleInput } from "../components";

export const VEHICLE_NUMBER_LENGTH = 4;

export function sanitizeVehicleNumber(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, VEHICLE_NUMBER_LENGTH);
}

export function isValidVehicleNumber(value: string): boolean {
  return new RegExp(`^\\d{${VEHICLE_NUMBER_LENGTH}}$`).test(value);
}

interface ManualEntryScreenProps {
  onBack: () => void;
  onSubmit: (vehicleNumber: string) => void;
}

export function ManualEntryScreen({ onBack, onSubmit }: ManualEntryScreenProps) {
  const [value, setValue] = useState("");
  const valid = isValidVehicleNumber(value);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (valid) onSubmit(value);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex min-h-dvh w-full max-w-[430px] flex-col bg-paper px-6 pb-14 pt-5"
    >
      <BackBar onBack={onBack} />
      <div className="mt-[82px] flex flex-col gap-[22px]">
        <h1 className="m-0 text-[32px] font-extrabold leading-[1.08] tracking-[-0.02em]">
          Którym autobusem lub tramwajem jedziesz?
        </h1>
        <VehicleInput value={value} onChange={(v) => setValue(sanitizeVehicleNumber(v))} />
      </div>
      <Button
        type="submit"
        disabled={!valid}
        icon={<UiIcon name="search" size={22} strokeWidth={2.4} />}
        className="mt-auto"
      >
        Znajdź mój pojazd
      </Button>
    </form>
  );
}
