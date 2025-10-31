import React from "react";

export type POSCartLine = {
  id: string;
  name: string;
  sku?: string;
  qty: number;
  price: number;
  discount?: number;
  subtotal: number;
};

export type POSCartLinesProps = {
  items?: POSCartLine[];
  onQty?: (id: string, qty: number) => void;
  onRemove?: (id: string) => void;
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function CartLines({ items, onQty, onRemove }: POSCartLinesProps) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ color: "#9ca3af" }}>Carrito vacío</div>;
  }

  return (
    <div style={{ display: "grid", gap: 6 }}>
      {data.map((line) => (
        <div
          key={line.id}
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 80px 90px 100px 36px",
            gap: 8,
            alignItems: "center",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            borderRadius: 8,
            padding: 8,
          }}
        >
          <div>
            <div style={{ fontWeight: 700 }}>{line.name}</div>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>{line.sku ?? "—"}</div>
          </div>
          <input
            type="number"
            min={0}
            value={line.qty}
            onChange={(event) => onQty?.(line.id, Number(event.target.value || 0))}
            style={{ width: "100%", padding: 6, borderRadius: 8 }}
          />
          <div style={{ textAlign: "right" }}>{currency.format(line.price)}</div>
          <div style={{ textAlign: "right" }}>{currency.format(line.subtotal)}</div>
          <button
            onClick={() => onRemove?.(line.id)}
            style={{ padding: "6px 8px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export default CartLines;
