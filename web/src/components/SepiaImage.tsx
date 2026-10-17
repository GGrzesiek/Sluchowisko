export function SepiaImage({ src, alt }: { src: string; alt: string }) {
  return <img src={src} alt={alt} className="block h-full w-full object-cover [filter:sepia(0.25)_contrast(1.05)]" />;
}
