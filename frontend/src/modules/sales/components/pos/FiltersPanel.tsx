import React from "react";

type AvailabilityFilter = "IN_STOCK" | "OUT_OF_STOCK";

export type POSFilters = {
  storeId?: string;
  category?: string;
  brand?: string;
  availability?: AvailabilityFilter;
};

type Props = {
  value: POSFilters;
  onChange: (next: POSFilters) => void;
};

export default function FiltersPanel({ value, onChange }: Props) {
  const v = value || {};
  return (
    <div className="pos-filters-panel">
      <input
        placeholder="Sucursal ID"
        value={v.storeId || ""}
        onChange={(e) => {
          const next: POSFilters = { ...v };
          const value = e.target.value.trim();
          if (value) {
            next.storeId = value;
          } else {
            delete next.storeId;
          }
          onChange(next);
        }}
        className="pos-filters-input"
      />
      <input
        placeholder="Categoría"
        value={v.category || ""}
        onChange={(e) => {
          const next: POSFilters = { ...v };
          const value = e.target.value.trim();
          if (value) {
            next.category = value;
          } else {
            delete next.category;
          }
          onChange(next);
        }}
        className="pos-filters-input"
      />
      <input
        placeholder="Marca"
        value={v.brand || ""}
        onChange={(e) => {
          const next: POSFilters = { ...v };
          const value = e.target.value.trim();
          if (value) {
            next.brand = value;
          } else {
            delete next.brand;
          }
          onChange(next);
        }}
        className="pos-filters-input"
      />
      <select
        value={v.availability || "ALL"}
        onChange={(e) => {
          const selected = e.target.value as AvailabilityFilter | "ALL";
          const next: POSFilters = { ...v };
          if (selected === "ALL") {
            delete next.availability;
          } else {
            next.availability = selected;
          }
          onChange(next);
        }}
        className="pos-filters-select"
      >
        <option value="ALL">Disponibilidad (todas)</option>
        <option value="IN_STOCK">En stock</option>
        <option value="OUT_OF_STOCK">Sin stock</option>
      </select>
    </div>
  );
}
