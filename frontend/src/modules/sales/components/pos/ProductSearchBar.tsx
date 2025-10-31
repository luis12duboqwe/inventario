import React from "react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSearch?: (query: string) => void;
};

export default function ProductSearchBar({ value, onChange, onSearch }: Props) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
      <input
        placeholder="Buscar SKU / IMEI / nombre"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            onSearch?.(value);
          }
        }}
        style={{ padding: 10, borderRadius: 10 }}
      />
      <button
        onClick={() => onSearch?.(value)}
        style={{ padding: "10px 14px", borderRadius: 10 }}
      >
        Buscar
      </button>
    </div>
  );
}
