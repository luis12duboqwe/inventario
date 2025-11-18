import React from "react";

export type OrderItem = {
  id: string;
  sku?: string;
  name: string;
  imei?: string;
  serial?: string;
  qty: number;
  price: number;
  discount?: number;
  subtotal: number;
};

export type OrderItemsTableProps = {
  items?: OrderItem[];
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function ItemsTable({ items }: OrderItemsTableProps) {
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
            <th style={{ textAlign: "left", padding: 10 }}>IMEI/Serial</th>
            <th style={{ textAlign: "center", padding: 10 }}>Cant.</th>
            <th style={{ textAlign: "right", padding: 10 }}>Precio</th>
            <th style={{ textAlign: "right", padding: 10 }}>Desc.</th>
            <th style={{ textAlign: "right", padding: 10 }}>Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.id}>
              <td style={{ padding: 10 }}>{item.sku ?? "—"}</td>
              <td style={{ padding: 10 }}>{item.name}</td>
              <td style={{ padding: 10 }}>{item.imei ?? item.serial ?? "—"}</td>
              <td style={{ padding: 10, textAlign: "center" }}>{item.qty}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{currency.format(item.price)}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{currency.format(item.discount ?? 0)}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{currency.format(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ItemsTable;
