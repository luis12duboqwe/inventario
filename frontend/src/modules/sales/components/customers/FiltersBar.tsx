import React from "react";

type Filters = {
  query?: string;
  tag?: string;
  tier?: string;
};

type Props = {
  value: Filters;
  onChange: (value: Filters) => void;
};

export default function FiltersBar({ value, onChange }: Props) {
  const current = value ?? {};
  return (
    <div className="customer-filters-bar">
      <input
        placeholder="Nombre/Telefono/Email"
        value={current.query ?? ""}
        onChange={(event) => onChange({ ...current, query: event.target.value })}
        className="customer-filters-input"
      />
      <input
        placeholder="Etiqueta"
        value={current.tag ?? ""}
        onChange={(event) => onChange({ ...current, tag: event.target.value })}
        className="customer-filters-input"
      />
      <input
        placeholder="Tier"
        value={current.tier ?? ""}
        onChange={(event) => onChange({ ...current, tier: event.target.value })}
        className="customer-filters-input"
      />
    </div>
  );
}
