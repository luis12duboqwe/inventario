import React from "react";

type Props = {
  mode: "grid" | "table";
  onChange: (mode: "grid" | "table") => void;
};

export default function ViewSwitch({ mode, onChange }: Props) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <button
        onClick={() => onChange("grid")}
        style={{
          padding: "6px 12px",
          borderRadius: 8,
          background: mode === "grid" ? "#2563eb" : "rgba(255,255,255,0.08)",
          color: "#fff",
          border: 0,
        }}
      >
        Grid
      </button>
      <button
        onClick={() => onChange("table")}
        style={{
          padding: "6px 12px",
          borderRadius: 8,
          background: mode === "table" ? "#2563eb" : "rgba(255,255,255,0.08)",
          color: "#fff",
          border: 0,
        }}
      >
        Tabla
      </button>
    </div>
  );
}
