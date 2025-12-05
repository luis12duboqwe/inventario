import React from "react";
import TextField from "../../../../../components/ui/TextField";
import { FILTER_ALL_VALUE, FILTER_ALL_LABEL } from "../../../../../config/constants";

type StoreOption = { id: number; name: string }; // [PACK30-31-FRONTEND]

type ProductStatus = "ACTIVE" | "INACTIVE" | typeof FILTER_ALL_VALUE;

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
    <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3 items-end">
      <TextField
        label="Buscar"
        hideLabel
        placeholder="Buscar (nombre o SKU)"
        value={v.query || ""}
        onChange={(event) => onChange({ ...v, query: event.target.value })}
      />

      <div className="ui-field">
        <div className="ui-field__control">
          <select
            className="ui-field__input cursor-pointer"
            value={v.status || FILTER_ALL_VALUE}
            onChange={(event) => {
              const selected = event.target.value as ProductStatus;
              const next: ProductFilters = { ...v };
              next.status = selected;
              onChange(next);
            }}
          >
            <option value={FILTER_ALL_VALUE}>{FILTER_ALL_LABEL}</option>
            <option value="ACTIVE">Activos</option>
            <option value="INACTIVE">Inactivos</option>
          </select>
        </div>
      </div>

      <TextField
        label="Categoría"
        hideLabel
        placeholder="Categoría ID"
        value={v.categoryId || ""}
        onChange={(event) => onChange({ ...v, categoryId: event.target.value })}
      />

      <div className="ui-field">
        <div className="ui-field__control">
          <select
            className="ui-field__input cursor-pointer"
            value={v.storeId ?? ""}
            onChange={(event) =>
              onChange({
                ...v,
                storeId: event.target.value ? Number(event.target.value) : null,
              })
            }
          >
            <option value="">Todas las sucursales</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <label className="ui-field__control cursor-pointer justify-center select-none h-[42px]">
        <input
          type="checkbox"
          checked={!!v.lowStock}
          onChange={(event) => onChange({ ...v, lowStock: event.target.checked })}
          className="w-[1.1rem] h-[1.1rem] accent-accent"
        />
        <span className="text-sm text-text-primary">Stock bajo</span>
      </label>

      <TextField
        label="Min"
        hideLabel
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
      />

      <TextField
        label="Max"
        hideLabel
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
      />
    </div>
  );
}
