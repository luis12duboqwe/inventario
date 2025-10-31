import React from "react";

type Props = {
  title: string;
  rows: [string, string | number][];
  onClose?: () => void;
};

export default function SidePanel({ title, rows, onClose }: Props) {
  return (
    <aside
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 420,
        background: "#0b1220",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        overflow: "auto",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <h3 style={{ margin: 0 }}>{title}</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {(rows ?? []).map(([label, value], index) => (
          <div
            key={index}
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderBottom: "1px dashed rgba(255,255,255,0.08)",
              padding: "6px 0",
            }}
          >
            <span style={{ color: "#94a3b8" }}>{label}</span>
            <span>{String(value)}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
