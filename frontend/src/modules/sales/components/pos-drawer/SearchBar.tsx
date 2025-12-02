import React from "react";

export type POSSearchBarProps = {
  value?: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
};

function SearchBar({ value, onChange, onSubmit }: POSSearchBarProps) {
  return (
    <div className="pos-search-bar">
      <input
        placeholder="Buscar por nombre, SKU o IMEI…"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        className="pos-search-input"
      />
      <button onClick={onSubmit} className="pos-search-btn">
        Buscar
      </button>
    </div>
  );
}

export default SearchBar;
