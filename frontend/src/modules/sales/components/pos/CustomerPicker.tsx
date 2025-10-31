import React from "react";

export type Customer = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
};

type Props = {
  customer?: Customer | null;
  onPick?: () => void;
  onClear?: () => void;
};

export default function CustomerPicker({ customer, onPick, onClear }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Cliente</div>
        {customer ? (
          <div style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
            <strong>{customer.name}</strong>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>
              {customer.phone || customer.email || ""}
            </span>
          </div>
        ) : (
          <div style={{ color: "#9ca3af" }}>Sin cliente</div>
        )}
      </div>
      <button
        onClick={onPick}
        style={{ padding: "8px 12px", borderRadius: 8, background: "rgba(255,255,255,0.08)", color: "#e5e7eb", border: 0 }}
      >
        Seleccionar
      </button>
      {customer ? (
        <button onClick={onClear} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Quitar
        </button>
      ) : null}
    </div>
  );
}
