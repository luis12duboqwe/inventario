import React from "react";

type Event = {
  id: string;
  date: string;
  message: string;
};

type Props = {
  items?: Event[];
};

export default function ActivityTimeline({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>Actividad</div>
      {data.length === 0 ? (
        <div style={{ color: "#9ca3af" }}>Sin actividad</div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {data.map((event) => (
            <div key={event.id} style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{new Date(event.date).toLocaleString()}</span>
              <span>{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
