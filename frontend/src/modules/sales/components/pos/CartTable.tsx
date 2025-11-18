import React from "react";

const formatter = new Intl.NumberFormat("es-HN", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 2,
});

export type CartItem = {
  id: string;
  sku: string;
  name: string;
  price: number;
  qty: number;
  discount?: number;
};

type Props = {
  items?: CartItem[];
  onInc?: (id: string) => void;
  onDec?: (id: string) => void;
  onRemove?: (id: string) => void;
  onEditDiscount?: (id: string) => void;
};

export default function CartTable({ items, onInc, onDec, onRemove, onEditDiscount }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (!data.length) return <div style={{ padding: 12, color: "#9ca3af" }}>Carrito vacío</div>;

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)" }}>
            <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
            <th style={{ textAlign: "left", padding: 10 }}>Producto</th>
            <th style={{ textAlign: "right", padding: 10 }}>Precio</th>
            <th style={{ textAlign: "center", padding: 10 }}>Cant.</th>
            <th style={{ textAlign: "right", padding: 10 }}>Desc.</th>
            <th style={{ textAlign: "right", padding: 10 }}>Subtotal</th>
            <th style={{ textAlign: "center", padding: 10 }}>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => {
            const discount = r.discount || 0;
            const subtotal = r.qty * r.price - discount;
            return (
              <tr key={r.id}>
                <td style={{ padding: 10 }}>{r.sku}</td>
                <td style={{ padding: 10 }}>{r.name}</td>
                <td style={{ padding: 10, textAlign: "right" }}>{formatter.format(r.price)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>
                  <div style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                    <button
                      onClick={() => onDec?.(r.id)}
                      style={{ padding: "4px 8px", borderRadius: 8 }}
                      disabled={r.qty <= 1}
                    >
                      -
                    </button>
                    <span>{r.qty}</span>
                    <button onClick={() => onInc?.(r.id)} style={{ padding: "4px 8px", borderRadius: 8 }}>
                      +
                    </button>
                  </div>
                </td>
                <td style={{ padding: 10, textAlign: "right" }}>
                  <button
                    onClick={() => onEditDiscount?.(r.id)}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 8,
                      background: "rgba(255,255,255,0.08)",
                      color: "#e5e7eb",
                      border: 0,
                    }}
                  >
                    {discount ? `-${formatter.format(discount)}` : "Agregar"}
                  </button>
                </td>
                <td style={{ padding: 10, textAlign: "right" }}>{formatter.format(subtotal)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>
                  <button
                    onClick={() => onRemove?.(r.id)}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 8,
                      background: "#b91c1c",
                      color: "#fff",
                      border: 0,
                    }}
                  >
                    Quitar
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
