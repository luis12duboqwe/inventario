import React from "react";

export type OrderNotesProps = {
  value?: string | null;
};

function Notes({ value }: OrderNotesProps) {
  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        whiteSpace: "pre-wrap",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>Notas</div>
      <div>{value && value.trim().length > 0 ? value : "—"}</div>
    </div>
  );
}

export default Notes;
