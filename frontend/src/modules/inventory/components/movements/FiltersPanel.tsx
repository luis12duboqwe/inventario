import React from "react";
import { FILTER_ALL_VALUE, FILTER_ALL_LABEL } from "../../../../../config/constants";

type MovementType = "IN" | "OUT" | "TRANSFER";

export type MovementFilters = {
  query?: string;
  type?: MovementType;
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
        value={v.type || FILTER_ALL_VALUE}
        onChange={(e) => {
          const selected = e.target.value as MovementType | typeof FILTER_ALL_VALUE;
          const next: MovementFilters = { ...v };
          if (selected === FILTER_ALL_VALUE) {
            delete next.type;
          } else {
            next.type = selected;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value={FILTER_ALL_VALUE}>{FILTER_ALL_LABEL}</option>
        <option value="IN">Entrada</option>
        <option value="OUT">Salida</option>
        <option value="TRANSFER">Transferencia</option>
      </select>
      <input
        placeholder="Sucursal (storeId)"
        value={v.storeId || ""}
        onChange={(e) => {
          const next: MovementFilters = { ...v };
          const value = e.target.value.trim();
          if (value) {
            next.storeId = value;
          } else {
            delete next.storeId;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="De (fromStoreId)"
        value={v.fromStoreId || ""}
        onChange={(e) => {
          const next: MovementFilters = { ...v };
          const value = e.target.value.trim();
          if (value) {
            next.fromStoreId = value;
          } else {
            delete next.fromStoreId;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="A (toStoreId)"
        value={v.toStoreId || ""}
        onChange={(e) => {
          const next: MovementFilters = { ...v };
          const value = e.target.value.trim();
          if (value) {
            next.toStoreId = value;
          } else {
            delete next.toStoreId;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateFrom || ""}
        onChange={(e) => {
          const next: MovementFilters = { ...v };
          const value = e.target.value;
          if (value) {
            next.dateFrom = value;
          } else {
            delete next.dateFrom;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateTo || ""}
        onChange={(e) => {
          const next: MovementFilters = { ...v };
          const value = e.target.value;
          if (value) {
            next.dateTo = value;
          } else {
            delete next.dateTo;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}
