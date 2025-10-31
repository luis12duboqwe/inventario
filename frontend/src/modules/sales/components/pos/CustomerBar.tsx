import React from "react";

type Customer = {
  id: string;
  name: string;
  phone?: string;
  tier?: string;
};

type Props = {
  customer?: Customer | null;
  onPick?: () => void;
  onQuickNew?: () => void;
};

export default function CustomerBar({ customer, onPick, onQuickNew }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Cliente</div>
        <div style={{ fontWeight: 700 }}>{customer?.name ?? "Mostrador"}</div>
        {!!customer?.phone && (
          <div style={{ fontSize: 12, color: "#94a3b8" }}>{customer.phone}</div>
        )}
      </div>
      <button onClick={onPick} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Buscar
      </button>
      <button onClick={onQuickNew} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Nuevo
      </button>
    </div>
  );
}
