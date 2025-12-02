import React from "react";

type Props = {
  className?: string;
  width?: string | number;
  height?: string | number;
  variant?: "text" | "circular" | "rectangular";
  lines?: number;
  style?: React.CSSProperties;
};

export function Skeleton({
  className = "",
  width,
  height,
  variant = "rectangular",
  lines = 1,
  style: customStyle,
}: Props) {
  const style: React.CSSProperties = { ...customStyle };
  if (width) style.width = width;
  if (height) style.height = height;

  if (lines > 1) {
    return (
      <div
        className={`ui-skeleton-group ${className}`}
        style={{ display: "flex", flexDirection: "column", gap: "8px", ...customStyle }}
      >
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`ui-skeleton ui-skeleton--${variant}`}
            style={style}
            aria-hidden="true"
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`ui-skeleton ui-skeleton--${variant} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}
