import React from "react";

export type MovementFilters = {
  query?: string;
  type?: "IN" | "OUT" | "TRANSFER" | "ALL";
  storeId?: string;
  fromStoreId?: string;
  toStoreId?: string;
  dateFrom?: string;
  dateTo?: string;
};

type Props = {
  value: MovementFilters;
  onChange: (next: MovementFilters) => void;
};

export default function FiltersPanel({ value, onChange }: Props) {
  const v = value || {};
  return (
    <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(6, minmax(160px,1fr))" }}>
      <input
        placeholder="Buscar por referencia/usuario…"
        value={v.query || ""}
        onChange={(e) => onChange({ ...v, query: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={v.type || "ALL"}
        onChange={(e) => onChange({ ...v, type: e.target.value as MovementFilters["type"] })}
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Todos</option>
        <option value="IN">Entrada</option>
        <option value="OUT">Salida</option>
        <option value="TRANSFER">Transferencia</option>
      </select>
      <input
        placeholder="Sucursal (storeId)"
        value={v.storeId || ""}
        onChange={(e) => onChange({ ...v, storeId: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="De (fromStoreId)"
        value={v.fromStoreId || ""}
        onChange={(e) => onChange({ ...v, fromStoreId: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="A (toStoreId)"
        value={v.toStoreId || ""}
        onChange={(e) => onChange({ ...v, toStoreId: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateFrom || ""}
        onChange={(e) => onChange({ ...v, dateFrom: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateTo || ""}
        onChange={(e) => onChange({ ...v, dateTo: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}
