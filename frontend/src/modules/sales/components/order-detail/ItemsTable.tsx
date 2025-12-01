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
    return <div className="order-items-empty">Sin items</div>;
  }

  return (
    <div className="order-items-container">
      <table className="order-items-table">
        <thead>
          <tr className="order-items-header-row">
            <th className="order-items-th-left">SKU</th>
            <th className="order-items-th-left">Producto</th>
            <th className="order-items-th-left">IMEI/Serial</th>
            <th className="order-items-th-center">Cant.</th>
            <th className="order-items-th-right">Precio</th>
            <th className="order-items-th-right">Desc.</th>
            <th className="order-items-th-right">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.id}>
              <td className="order-items-td">{item.sku ?? "—"}</td>
              <td className="order-items-td">{item.name}</td>
              <td className="order-items-td">{item.imei ?? item.serial ?? "—"}</td>
              <td className="order-items-td-center">{item.qty}</td>
              <td className="order-items-td-right">{currency.format(item.price)}</td>
              <td className="order-items-td-right">{currency.format(item.discount ?? 0)}</td>
              <td className="order-items-td-right">{currency.format(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ItemsTable;
