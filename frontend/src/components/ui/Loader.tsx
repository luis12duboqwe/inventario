import React from "react";
import { Skeleton } from "./Skeleton";

type LoaderProps = {
  /** spinner | skeleton | overlay | compact (default: spinner) */
  variant?: "spinner" | "skeleton" | "overlay" | "compact";
  /** Alto del skeleton (cuando variant === "skeleton") */
  height?: number | string;
  /** Ancho del skeleton (cuando variant === "skeleton") */
  width?: number | string;
  /** Texto accesible */
  label?: string;
  /** Alias legado usado en pruebas/mocks (se mapea a label) */
  message?: string;
  /** Clase externa opcional */
  className?: string;
};

const Spinner = () => <div className="loader-spinner" />;

export const Loader: React.FC<LoaderProps> = ({
  variant = "spinner",
  height,
  width,
  label,
  message,
  className,
}) => {
  const displayLabel = message ?? label ?? "Cargando…";

  if (variant === "overlay") {
    return (
      <div aria-label={displayLabel} role="status" className={`loader-overlay ${className || ""}`}>
        <Spinner />
      </div>
    );
  }

  if (variant === "skeleton") {
    return (
      <div aria-label={displayLabel} role="status" className={className}>
        <Skeleton height={height} width={width} />
      </div>
    );
  }

  // compact or spinner
  return (
    <div aria-label={displayLabel} role="status" className={`loader-compact ${className || ""}`}>
      <Spinner />
      <span className="loader-label">{displayLabel}</span>
    </div>
  );
};

export default Loader;
