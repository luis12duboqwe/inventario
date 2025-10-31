import React from "react";

type Item = {
  id: string;
  sku: string;
  name: string;
  cost: number;
  qty: number;
  received?: number;
};

type Props = {
  items?: Item[];
};

export default function ItemsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin items</div>;
  }

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255, 255, 255, 0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255, 255, 255, 0.03)" }}>
            <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
            <th style={{ textAlign: "left", padding: 10 }}>Producto</th>
            <th style={{ textAlign: "right", padding: 10 }}>Costo</th>
            <th style={{ textAlign: "center", padding: 10 }}>Cant.</th>
            <th style={{ textAlign: "center", padding: 10 }}>Recibido</th>
            <th style={{ textAlign: "right", padding: 10 }}>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => {
            const subtotal = item.qty * item.cost;
            return (
              <tr key={item.id}>
                <td style={{ padding: 10 }}>{item.sku}</td>
                <td style={{ padding: 10 }}>{item.name}</td>
                <td style={{ padding: 10, textAlign: "right" }}>{Intl.NumberFormat().format(item.cost)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>{item.qty}</td>
                <td style={{ padding: 10, textAlign: "center" }}>{item.received ?? 0}</td>
                <td style={{ padding: 10, textAlign: "right" }}>{Intl.NumberFormat().format(subtotal)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
