import React from "react";

type Props = {
  summary: Record<string, unknown>;
  onSubmit: () => void;
};

export default function StepReview({ summary, onSubmit }: Props) {
  const data = summary || {};

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div
        style={{
          padding: 12,
          borderRadius: 12,
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Resumen</div>
        <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(data, null, 2)}</pre>
      </div>
      <div>
        <button
          onClick={onSubmit}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
          type="button"
        >
          Crear movimiento
        </button>
      </div>
    </div>
  );
}
