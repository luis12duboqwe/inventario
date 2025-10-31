import React from "react";

type Filters = {
  query?: string;
  status?: "ALL" | "DRAFT" | "SENT" | "PARTIAL" | "RECEIVED" | "CANCELLED";
  supplier?: string;
  dateFrom?: string;
  dateTo?: string;
};

type Props = {
  value: Filters;
  onChange: (v: Filters) => void;
  onNew?: () => void;
};

const gridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr auto",
  gap: 8,
};

const inputStyle: React.CSSProperties = {
  padding: 8,
  borderRadius: 8,
  background: "rgba(15, 23, 42, 0.9)",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  color: "#e5e7eb",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  background: "rgba(37, 99, 235, 0.12)",
  color: "#60a5fa",
  border: "1px solid rgba(37, 99, 235, 0.4)",
};

export default function FiltersBar({ value, onChange, onNew }: Props) {
  const v = value || {};
  return (
    <div style={gridStyle}>
      <input
        placeholder="Proveedor o #PO"
        value={v.query || ""}
        onChange={(event) => onChange({ ...v, query: event.target.value })}
        style={inputStyle}
      />
      <select
        value={v.status || "ALL"}
        onChange={(event) => onChange({ ...v, status: event.target.value as Filters["status"] })}
        style={inputStyle}
      >
        <option value="ALL">Estado</option>
        <option value="DRAFT">Borrador</option>
        <option value="SENT">Enviado</option>
        <option value="PARTIAL">Parcial</option>
        <option value="RECEIVED">Recibido</option>
        <option value="CANCELLED">Cancelado</option>
      </select>
      <input
        placeholder="Proveedor"
        value={v.supplier || ""}
        onChange={(event) => onChange({ ...v, supplier: event.target.value })}
        style={inputStyle}
      />
      <input
        type="date"
        value={v.dateFrom || ""}
        onChange={(event) => onChange({ ...v, dateFrom: event.target.value })}
        style={inputStyle}
      />
      <input
        type="date"
        value={v.dateTo || ""}
        onChange={(event) => onChange({ ...v, dateTo: event.target.value })}
        style={inputStyle}
      />
      <button type="button" onClick={onNew} style={buttonStyle}>
        Nueva PO
      </button>
    </div>
  );
}
