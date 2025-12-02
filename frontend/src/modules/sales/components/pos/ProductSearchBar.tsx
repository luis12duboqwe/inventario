import React from "react";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSearch?: (query: string) => void;
};

export default function ProductSearchBar({ value, onChange, onSearch }: Props) {
  return (
    <div className="pos-product-search-bar">
      <input
        id="pos-product-search"
        placeholder="Buscar SKU / IMEI / nombre"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            onSearch?.(value);
          }
        }}
        className="pos-product-search-input"
      />
      <button onClick={() => onSearch?.(value)} className="pos-product-search-btn">
        Buscar
      </button>
    </div>
  );
}
