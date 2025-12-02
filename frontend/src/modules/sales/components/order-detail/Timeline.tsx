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
    <div className="order-timeline-card">
      <span className="order-timeline-label">Actividad</span>
      {data.length === 0 ? (
        <span className="order-timeline-empty">Sin actividad</span>
      ) : (
        <div className="order-timeline-list">
          {data.map((event) => (
            <div key={event.id} className="order-timeline-item">
              <span className="order-timeline-date">{new Date(event.date).toLocaleString()}</span>
              <span>{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Timeline;
