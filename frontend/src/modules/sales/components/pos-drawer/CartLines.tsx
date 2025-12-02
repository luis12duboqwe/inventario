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

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function CartLines({ items, onQty, onRemove }: POSCartLinesProps) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div className="pos-cart-empty">Carrito vacío</div>;
  }

  return (
    <div className="pos-cart-lines">
      {data.map((line) => (
        <div key={line.id} className="pos-cart-line">
          <div>
            <div className="pos-cart-line-name">{line.name}</div>
            <div className="pos-cart-line-sku">{line.sku ?? "—"}</div>
          </div>
          <input
            type="number"
            min={0}
            value={line.qty}
            onChange={(event) => onQty?.(line.id, Number(event.target.value || 0))}
            className="pos-cart-line-qty"
          />
          <div className="pos-cart-line-price">{currency.format(line.price)}</div>
          <div className="pos-cart-line-subtotal">{currency.format(line.subtotal)}</div>
          <button onClick={() => onRemove?.(line.id)} className="pos-cart-line-remove">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export default CartLines;
