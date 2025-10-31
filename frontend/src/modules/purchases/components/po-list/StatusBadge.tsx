import React from "react";

type Props = {
  value: string;
};

export default function StatusBadge({ value }: Props) {
  const map: Record<string, string> = {
    DRAFT: "#6b7280",
    OPEN: "#2563eb",
    PARTIAL: "#f59e0b",
    RECEIVED: "#16a34a",
    CANCELLED: "#b91c1c",
  };
  const background = map[value] || "#6b7280";
  return (
    <span
      style={{
        padding: "2px 8px",
        borderRadius: 999,
        background,
        color: "#0b1220",
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {value}
    </span>
  );
}
