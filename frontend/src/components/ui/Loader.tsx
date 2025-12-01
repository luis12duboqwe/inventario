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

const Spinner = () => (
  <div
    style={{
      display: "inline-block",
      width: 24,
      height: 24,
      border: "3px solid #4b5563",
      borderTopColor: "#60a5fa",
      borderRadius: "50%",
      animation: "spin 0.8s linear infinite",
    }}
  />
);

const overlayStyle: React.CSSProperties = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  backdropFilter: "blur(2px)",
  background: "rgba(0,0,0,0.25)",
  zIndex: 50,
};

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
      <div aria-label={displayLabel} role="status" className={className} style={overlayStyle}>
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
    <div
      aria-label={displayLabel}
      role="status"
      className={className}
      style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
    >
      <Spinner />
      <span style={{ fontSize: 12, color: "#9ca3af" }}>{displayLabel}</span>
      <style>{`@keyframes spin {to { transform: rotate(360deg); }}`}</style>
    </div>
  );
};

export default Loader;
