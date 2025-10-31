import React from "react";

type Props = {
  value?: string;
};

export default function Notes({ value }: Props) {
  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>Notas</div>
      <div style={{ whiteSpace: "pre-wrap" }}>{value || "—"}</div>
    </div>
  );
}
