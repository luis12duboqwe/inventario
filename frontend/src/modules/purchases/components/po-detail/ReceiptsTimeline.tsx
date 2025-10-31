import React from "react";

type Receipt = {
  id: string;
  date: string;
  qty: number;
  note?: string;
};

type Props = {
  items?: Receipt[];
};

export default function ReceiptsTimeline({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>Recepciones</div>
      {data.length === 0 ? (
        <div style={{ color: "#9ca3af" }}>Sin recepciones</div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {data.map((entry) => (
            <div key={entry.id} style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{new Date(entry.date).toLocaleString()}</span>
              <span>{entry.qty}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
