import type { ReactNode } from "react";
import { BackBar } from "../components";

export function PlaceholderScreen({
  title,
  onBack,
  children,
}: {
  title: string;
  onBack?: () => void;
  children?: ReactNode;
}) {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col gap-6 bg-paper px-6 py-5 text-charcoal">
      {onBack && <BackBar onBack={onBack} />}
      <h1 className="m-0 text-[32px] font-extrabold leading-tight tracking-[-0.02em]">{title}</h1>
      {children}
    </main>
  );
}
