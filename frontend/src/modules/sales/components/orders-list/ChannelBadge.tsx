import React from "react";

export type ChannelBadgeProps = {
  value: "POS" | "WEB" | "MANUAL" | string;
};

const CHANNEL_COLORS: Record<string, string> = {
  POS: "#2563eb",
  WEB: "#9333ea",
  MANUAL: "#94a3b8",
};

function ChannelBadge({ value }: ChannelBadgeProps) {
  const background = CHANNEL_COLORS[value] ?? "#6b7280";

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

export default ChannelBadge;
