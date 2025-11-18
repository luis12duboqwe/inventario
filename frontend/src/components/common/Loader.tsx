import React from "react";

type LoaderProps = {
  /** spinner | skeleton | overlay (default: spinner) */
  variant?: "spinner" | "skeleton" | "overlay";
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
  <div style={{ display: "inline-block", width: 24, height: 24, border: "3px solid #4b5563", borderTopColor: "#60a5fa", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
);

const Skeleton: React.FC<{ height?: number | string; width?: number | string }> = ({ height = 18, width = "100%" }) => (
  <div style={{ width, height, borderRadius: 8, background: "linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.12) 37%, rgba(255,255,255,0.06) 63%)", backgroundSize: "400% 100%", animation: "skeleton 1.2s ease-in-out infinite" }} />
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
    const skeletonProps: { height?: number | string; width?: number | string } = {};
    if (typeof height !== "undefined") {
      skeletonProps.height = height;
    }
    if (typeof width !== "undefined") {
      skeletonProps.width = width;
    }
    return (
      <div aria-label={displayLabel} role="status" className={className}>
        <Skeleton {...skeletonProps} />
      </div>
    );
  }
  return (
    <div aria-label={displayLabel} role="status" className={className} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <Spinner />
      <span style={{ fontSize: 12, color: "#9ca3af" }}>{displayLabel}</span>
      <style>
        {`@keyframes spin {to { transform: rotate(360deg); }}
          @keyframes skeleton { 0%{background-position: 100% 50%} 100%{background-position: 0 50%} }`}
      </style>
    </div>
  );
};

export default Loader;
