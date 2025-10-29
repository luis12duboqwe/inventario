import React from "react";

export type ProductFilters = {
  query?: string;
  status?: "ACTIVE" | "INACTIVE" | "ALL";
  categoryId?: string;
  lowStock?: boolean;
  priceMin?: number;
  priceMax?: number;
};

type Props = {
  value: ProductFilters;
  onChange: (next: ProductFilters) => void;
};

export default function FiltersBar({ value, onChange }: Props) {
  const v = value || {};

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr",
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
        onChange={(event) =>
          onChange({ ...v, status: event.target.value as ProductFilters["status"] })
        }
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
        onChange={(event) =>
          onChange({
            ...v,
            priceMin: event.target.value ? Number(event.target.value) : undefined,
          })
        }
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="number"
        placeholder="Precio max"
        value={v.priceMax ?? ""}
        onChange={(event) =>
          onChange({
            ...v,
            priceMax: event.target.value ? Number(event.target.value) : undefined,
          })
        }
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}
