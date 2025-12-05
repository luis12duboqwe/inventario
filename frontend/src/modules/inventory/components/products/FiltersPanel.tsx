import React from "react";
import { TextField } from "../../../../../components/ui/TextField";

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
    <div className="grid gap-2 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
      <TextField
        placeholder="Buscar por nombre, SKU o IMEI…"
        value={v.query || ""}
        onChange={(e) => onChange({ ...v, query: e.target.value })}
      />
      <TextField
        placeholder="Categoría"
        value={v.category || ""}
        onChange={(e) => onChange({ ...v, category: e.target.value })}
      />
      <TextField
        placeholder="Marca"
        value={v.brand || ""}
        onChange={(e) => onChange({ ...v, brand: e.target.value })}
      />
      <TextField
        placeholder="Sucursal ID"
        value={v.storeId || ""}
        onChange={(e) => onChange({ ...v, storeId: e.target.value })}
      />
      <TextField
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
      />
      <TextField
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
      />
      {/* estado si aplica */}
    </div>
  );
}
