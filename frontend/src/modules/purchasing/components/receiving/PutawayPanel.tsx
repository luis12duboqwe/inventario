import React from "react";

const containerStyle: React.CSSProperties = {
  padding: 8,
  borderRadius: 8,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 8,
};

export default function PutawayPanel() {
  return (
    <div style={containerStyle}>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Ubicación (opcional)</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <input placeholder="Almacén" style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }} />
        <input placeholder="Ubicación" style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }} />
      </div>
    </div>
  );
}
