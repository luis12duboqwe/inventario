import React from "react";

export type StatusBadgeProps = {
  value: "DRAFT" | "OPEN" | "COMPLETED" | "CANCELLED" | string;
};

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "#6b7280",
  OPEN: "#0ea5e9",
  COMPLETED: "#16a34a",
  CANCELLED: "#b91c1c",
};

function StatusBadge({ value }: StatusBadgeProps) {
  const background = STATUS_COLORS[value] ?? "#6b7280";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        background,
        color: "#0b1220",
        fontSize: 12,
        fontWeight: 700,
        textTransform: "uppercase",
      }}
    >
      {value}
    </span>
  );
}

export default StatusBadge;
