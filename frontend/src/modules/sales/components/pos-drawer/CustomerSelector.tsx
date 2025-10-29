import React from "react";

export type POSCustomer = {
  id: string;
  name: string;
  phone?: string;
};

export type POSCustomerSelectorProps = {
  customer?: POSCustomer | null;
  onPick?: () => void;
  onCreate?: () => void;
};

function CustomerSelector({ customer, onPick, onCreate }: POSCustomerSelectorProps) {
  return (
    <div style={{ display: "grid", gap: 6 }}>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Cliente</span>
      {customer ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: 8,
            borderRadius: 8,
            border: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <div>
            <strong>{customer.name}</strong>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>{customer.phone ?? ""}</div>
          </div>
          <button onClick={onPick} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Cambiar
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={onPick} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Seleccionar
          </button>
          <button onClick={onCreate} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Nuevo
          </button>
        </div>
      )}
    </div>
  );
}

export default CustomerSelector;
