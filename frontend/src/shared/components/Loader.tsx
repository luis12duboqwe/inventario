import { memo } from "react";

export type LoaderVariant = "overlay" | "compact";

type LoaderProps = {
  message?: string;
  variant?: LoaderVariant;
  className?: string;
};

const Loader = memo(function Loader({
  message = "Cargando…",
  variant = "overlay",
  className,
}: LoaderProps) {
  const overlayClass = variant === "compact" ? "loading-overlay compact" : "loading-overlay";
  const combinedClassName = className ? `${overlayClass} ${className}` : overlayClass;

  return (
    <div className={combinedClassName} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
});

export default Loader;
