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
    <div style={{ display: "flex", gap: 8 }}>
      <input
        ref={inputRef}
        autoFocus
        value={query || ""}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={(e) => (e.key === "Enter" ? onSubmit() : null)}
        placeholder={placeholder}
        style={{ flex: 1, padding: 10, borderRadius: 10 }}
      />
      <button
        onClick={onSubmit}
        style={{
          padding: "10px 14px",
          borderRadius: 10,
          background: "#2563eb",
          color: "#fff",
          border: 0,
        }}
      >
        Buscar
      </button>
    </div>
  );
}
