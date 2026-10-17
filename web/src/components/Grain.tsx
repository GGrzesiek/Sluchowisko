import { useId } from "react";

interface GrainProps {
  opacity?: number;
  baseFrequency?: number;
  octaves?: number;
  tint?: [number, number, number];
  alpha?: number;
}

export function Grain({
  opacity = 0.35,
  baseFrequency = 0.9,
  octaves = 3,
  tint = [0.45, 0.35, 0.22],
  alpha = 0.55,
}: GrainProps) {
  const id = `grain-${useId().replace(/:/g, "")}`;
  const [r, g, b] = tint;
  return (
    <svg
      width="100%"
      height="100%"
      className="pointer-events-none absolute inset-0 mix-blend-multiply"
      style={{ opacity }}
      aria-hidden="true"
    >
      <filter id={id}>
        <feTurbulence type="fractalNoise" baseFrequency={baseFrequency} numOctaves={octaves} stitchTiles="stitch" />
        <feColorMatrix values={`0 0 0 0 ${r}  0 0 0 0 ${g}  0 0 0 0 ${b}  0 0 0 ${alpha} 0`} />
      </filter>
      <rect width="100%" height="100%" filter={`url(#${id})`} />
    </svg>
  );
}
