import React from "react";

export type OrderNotesProps = {
  value?: string | null;
};

function Notes({ value }: OrderNotesProps) {
  return (
    <div className="order-notes-card">
      <div className="order-notes-label">Notas</div>
      <div>{value && value.trim().length > 0 ? value : "—"}</div>
    </div>
  );
}

export default Notes;
