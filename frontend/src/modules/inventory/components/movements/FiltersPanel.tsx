import React from "react";
import {
  MOVEMENT_FILTER_OPTIONS,
  type MovementFilterType,
} from "./constants";

export type MovementFilters = {
  query?: string;
  type?: MovementFilterType;
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
        onChange={(e) => onChange({ ...v, type: e.target.value as MovementFilterType })}
        style={{ padding: 8, borderRadius: 8 }}
      >
        {MOVEMENT_FILTER_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
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
