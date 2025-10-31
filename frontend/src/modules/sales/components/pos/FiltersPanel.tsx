import React from "react";

export type POSFilters = {
  storeId?: string;
  category?: string;
  brand?: string;
  availability?: "IN_STOCK" | "OUT_OF_STOCK" | "ALL";
};

type Props = {
  value: POSFilters;
  onChange: (next: POSFilters) => void;
};

export default function FiltersPanel({ value, onChange }: Props) {
  const v = value || {};
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(160px,1fr))",
        gap: 8,
      }}
    >
      <input
        placeholder="Sucursal ID"
        value={v.storeId || ""}
        onChange={(e) => onChange({ ...v, storeId: e.target.value })}
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
      <select
        value={v.availability || "ALL"}
        onChange={(e) => onChange({ ...v, availability: e.target.value as POSFilters["availability"] })}
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Disponibilidad (todas)</option>
        <option value="IN_STOCK">En stock</option>
        <option value="OUT_OF_STOCK">Sin stock</option>
      </select>
    </div>
  );
}
