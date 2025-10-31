import React from "react";

type Props = {
  value: "ACTIVE" | "INACTIVE" | string;
};

export default function StatusBadge({ value }: Props) {
  const map: Record<string, string> = { ACTIVE: "#22c55e", INACTIVE: "#6b7280" };
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
