import React from "react";

export type ProductFilters = {
  query?: string;
  category?: string;
  brand?: string;
  storeId?: string;
  stockFrom?: number;
  stockTo?: number;
  status?: string;
};

type Props = {
  value: ProductFilters;
  onChange: (next: ProductFilters) => void;
};

export default function FiltersPanel({ value, onChange }: Props) {
  const v = value || {};
  return (
    <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(6, minmax(140px,1fr))" }}>
      <input
        placeholder="Buscar por nombre, SKU o IMEI…"
        value={v.query || ""}
        onChange={(e) => onChange({ ...v, query: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Categoría"
        value={v.category || ""}
        onChange={(e) => onChange({ ...v, category: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Marca"
        value={v.brand || ""}
        onChange={(e) => onChange({ ...v, brand: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Sucursal ID"
        value={v.storeId || ""}
        onChange={(e) => onChange({ ...v, storeId: e.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="number"
        placeholder="Stock ≥"
        value={v.stockFrom ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          const next: ProductFilters = { ...v };
          if (raw) {
            next.stockFrom = Number(raw);
          } else {
            delete next.stockFrom;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="number"
        placeholder="Stock ≤"
        value={v.stockTo ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          const next: ProductFilters = { ...v };
          if (raw) {
            next.stockTo = Number(raw);
          } else {
            delete next.stockTo;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      {/* estado si aplica */}
    </div>
  );
}
