import React from "react";

export type OrderTimelineEvent = {
  id: string;
  date: string;
  message: string;
};

export type OrderTimelineProps = {
  items?: OrderTimelineEvent[];
};

function Timeline({ items }: OrderTimelineProps) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        display: "grid",
        gap: 8,
      }}
    >
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Actividad</span>
      {data.length === 0 ? (
        <span style={{ color: "#9ca3af" }}>Sin actividad</span>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {data.map((event) => (
            <div key={event.id} style={{ display: "grid", gap: 2 }}>
              <span style={{ fontSize: 11, color: "#94a3b8" }}>
                {new Date(event.date).toLocaleString()}
              </span>
              <span>{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Timeline;
