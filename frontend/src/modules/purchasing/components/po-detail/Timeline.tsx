import React from "react";

type Event = {
  id: string;
  date: string;
  message: string;
};

type Props = {
  items?: Event[];
};

const cardStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 8,
};

export default function Timeline({ items }: Props) {
  const data = Array.isArray(items) ? items : [];
  const sorted = [...data].sort((a, b) => {
    const first = new Date(a.date).getTime();
    const second = new Date(b.date).getTime();
    if (Number.isNaN(first) && Number.isNaN(second)) {
      return 0;
    }
    if (Number.isNaN(first)) {
      return 1;
    }
    if (Number.isNaN(second)) {
      return -1;
    }
    return first - second;
  });

  const formatDate = (value: string) => {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString("es-MX");
  };

  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Actividad</div>
      {data.length === 0 ? (
        <div style={{ color: "#9ca3af" }}>Sin actividad</div>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {sorted.map((event) => (
            <div key={event.id} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span>{formatDate(event.date)}</span>
              <span>{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
