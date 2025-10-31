import React from "react";

export type POSSearchBarProps = {
  value?: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
};

function SearchBar({ value, onChange, onSubmit }: POSSearchBarProps) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <input
        placeholder="Buscar por nombre, SKU o IMEI…"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        style={{ flex: 1, padding: 8, borderRadius: 8 }}
      />
      <button onClick={onSubmit} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Buscar
      </button>
    </div>
  );
}

export default SearchBar;
