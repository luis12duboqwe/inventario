import React from "react";

type StoreOption = { id: number; name: string }; // [PACK30-31-FRONTEND]

type ProductStatus = "ACTIVE" | "INACTIVE" | "ALL";

export type ProductFilters = {
  query?: string;
  status?: ProductStatus;
  categoryId?: string;
  lowStock?: boolean;
  priceMin?: number;
  priceMax?: number;
  storeId?: number | null;
};

type Props = {
  value: ProductFilters;
  onChange: (next: ProductFilters) => void;
  stores?: StoreOption[];
};

export default function FiltersBar({ value, onChange, stores = [] }: Props) {
  const v = value || {};

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr 1fr",
        gap: 8,
      }}
    >
      <input
        placeholder="Buscar (nombre o SKU)"
        value={v.query || ""}
        onChange={(event) => onChange({ ...v, query: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={v.status || "ALL"}
        onChange={(event) => {
          const selected = event.target.value as ProductStatus;
          const next: ProductFilters = { ...v };
          next.status = selected;
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Todos</option>
        <option value="ACTIVE">Activos</option>
        <option value="INACTIVE">Inactivos</option>
      </select>
      <input
        placeholder="Categoría ID"
        value={v.categoryId || ""}
        onChange={(event) => onChange({ ...v, categoryId: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={v.storeId ?? ""}
        onChange={(event) =>
          onChange({
            ...v,
            storeId: event.target.value ? Number(event.target.value) : null,
          })
        }
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="">Todas las sucursales</option>
        {stores.map((store) => (
          <option key={store.id} value={store.id}>
            {store.name}
          </option>
        ))}
      </select>
      <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <input
          type="checkbox"
          checked={!!v.lowStock}
          onChange={(event) => onChange({ ...v, lowStock: event.target.checked })}
        />
        Stock bajo
      </label>
      <input
        type="number"
        placeholder="Precio min"
        value={v.priceMin ?? ""}
        onChange={(event) => {
          const raw = event.target.value;
          const next: ProductFilters = { ...v };
          if (raw) {
            next.priceMin = Number(raw);
          } else {
            delete next.priceMin;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="number"
        placeholder="Precio max"
        value={v.priceMax ?? ""}
        onChange={(event) => {
          const raw = event.target.value;
          const next: ProductFilters = { ...v };
          if (raw) {
            next.priceMax = Number(raw);
          } else {
            delete next.priceMax;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}
