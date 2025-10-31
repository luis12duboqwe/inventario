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
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 8 }}>
      <input
        placeholder="Nombre/Telefono/Email"
        value={current.query ?? ""}
        onChange={(event) => onChange({ ...current, query: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Etiqueta"
        value={current.tag ?? ""}
        onChange={(event) => onChange({ ...current, tag: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Tier"
        value={current.tier ?? ""}
        onChange={(event) => onChange({ ...current, tier: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}
