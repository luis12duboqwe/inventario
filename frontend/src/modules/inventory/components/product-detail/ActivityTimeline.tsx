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
    <div className="p-3 rounded-xl bg-surface border border-border">
      <div className="text-xs text-muted-foreground mb-2">Actividad</div>
      {data.length === 0 ? (
        <div className="text-muted-foreground">Sin actividad</div>
      ) : (
        <div className="grid gap-2">
          {data.map((event) => (
            <div key={event.id} className="flex justify-between">
              <span>{new Date(event.date).toLocaleString()}</span>
              <span>{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
