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

  if (!data.length) return <div className="pos-cart-empty-message">Carrito vacío</div>;

  return (
    <div className="pos-cart-table-container">
      <table className="pos-cart-table">
        <thead>
          <tr className="pos-cart-table-header">
            <th className="pos-cart-table-th">SKU</th>
            <th className="pos-cart-table-th">Producto</th>
            <th className="pos-cart-table-th-right">Precio</th>
            <th className="pos-cart-table-th-center">Cant.</th>
            <th className="pos-cart-table-th-right">Desc.</th>
            <th className="pos-cart-table-th-right">Subtotal</th>
            <th className="pos-cart-table-th-center">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => {
            const discount = r.discount || 0;
            const subtotal = r.qty * r.price - discount;
            return (
              <tr key={r.id}>
                <td className="pos-cart-table-td">{r.sku}</td>
                <td className="pos-cart-table-td">{r.name}</td>
                <td className="pos-cart-table-td-right">{formatter.format(r.price)}</td>
                <td className="pos-cart-table-td-center">
                  <div className="pos-cart-qty-control">
                    <button
                      onClick={() => onDec?.(r.id)}
                      className="pos-cart-qty-button"
                      disabled={r.qty <= 1}
                    >
                      -
                    </button>
                    <span>{r.qty}</span>
                    <button onClick={() => onInc?.(r.id)} className="pos-cart-qty-button">
                      +
                    </button>
                  </div>
                </td>
                <td className="pos-cart-table-td-right">
                  <button
                    onClick={() => onEditDiscount?.(r.id)}
                    className="pos-cart-discount-button"
                  >
                    {discount ? `-${formatter.format(discount)}` : "Agregar"}
                  </button>
                </td>
                <td className="pos-cart-table-td-right">{formatter.format(subtotal)}</td>
                <td className="pos-cart-table-td-center">
                  <button onClick={() => onRemove?.(r.id)} className="pos-cart-remove-button">
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
