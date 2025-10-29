import React from "react";

type Item = {
  id: string;
  sku: string;
  name: string;
  price: number;
  qty: number;
  discount?: number;
};

type Props = {
  items?: Item[];
};

function ItemsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (!data.length) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin items</div>;
  }

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255, 255, 255, 0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255, 255, 255, 0.03)" }}>
            <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
            <th style={{ textAlign: "left", padding: 10 }}>Producto</th>
            <th style={{ textAlign: "right", padding: 10 }}>Precio</th>
            <th style={{ textAlign: "center", padding: 10 }}>Cant.</th>
            <th style={{ textAlign: "right", padding: 10 }}>Desc.</th>
            <th style={{ textAlign: "right", padding: 10 }}>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => {
            const discount = row.discount || 0;
            const subtotal = row.qty * row.price - discount;
            return (
              <tr key={row.id}>
                <td style={{ padding: 10 }}>{row.sku}</td>
                <td style={{ padding: 10 }}>{row.name}</td>
                <td style={{ padding: 10, textAlign: "right" }}>{Intl.NumberFormat().format(row.price)}</td>
                <td style={{ padding: 10, textAlign: "center" }}>{row.qty}</td>
                <td style={{ padding: 10, textAlign: "right" }}>
                  {discount ? `-${Intl.NumberFormat().format(discount)}` : "—"}
                </td>
                <td style={{ padding: 10, textAlign: "right" }}>{Intl.NumberFormat().format(subtotal)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default ItemsTable;
