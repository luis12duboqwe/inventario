import React from "react";

type Props = {
  query: string;
  onQueryChange: (text: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  inputRef?: React.Ref<HTMLInputElement>;
};

export default function SearchBar({
  query,
  onQueryChange,
  onSubmit,
  placeholder = "Buscar por nombre, SKU o IMEI…",
  inputRef,
}: Props) {
  return (
    <div className="pos-search-bar">
      <input
        ref={inputRef}
        value={query || ""}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={(e) => (e.key === "Enter" ? onSubmit() : null)}
        placeholder={placeholder}
        className="pos-search-input"
      />
      <button onClick={onSubmit} className="pos-search-btn">
        Buscar
      </button>
    </div>
  );
}
