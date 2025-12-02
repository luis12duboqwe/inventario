import React from "react";
// [PACK26-POS-CART-PERMS-START]
import { RequirePerm, PERMS } from "../../../../auth/useAuthz";
// [PACK26-POS-CART-PERMS-END]

type Discount = { type: "PERCENT" | "AMOUNT"; value: number } | null;

type Line = {
  id: string;
  sku?: string;
  name: string;
  qty: number;
  price: number;
  discount?: Discount;
  imei?: string;
  badges?: string[];
};

type Totals = {
  sub: number;
  disc: number;
  tax: number;
  grand: number;
};

type Props = {
  lines: Line[];
  totals: Totals;
  onQty: (id: string, qty: number) => void;
  onRemove: (id: string) => void;
  onDiscount: (id: string) => void;
  onOverridePrice: (id: string) => void;
};

export default function CartPanel({
  lines,
  totals,
  onQty,
  onRemove,
  onDiscount,
  onOverridePrice,
}: Props) {
  const data = Array.isArray(lines) ? lines : [];
  return (
    <div className="pos-cart-panel">
      <div className="pos-cart-panel__title">Carrito</div>
      <div className="pos-cart-list">
        {data.length ? (
          data.map((line) => (
            <div key={line.id} className="pos-cart-item">
              <div>
                <div className="pos-cart-item__name">{line.name}</div>
                <div className="pos-cart-item__meta">
                  {line.sku ?? "—"}
                  {line.imei ? ` · IMEI ${line.imei}` : ""}
                </div>
                {Array.isArray(line.badges) && line.badges.length > 0 && (
                  <div className="pos-cart-item__badges">
                    {line.badges.map((badge) => (
                      <span key={badge} className="pos-cart-item__badge">
                        {badge}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="pos-qty-stepper">
                <button
                  type="button"
                  onClick={() => onQty(line.id, line.qty - 1)}
                  disabled={line.qty <= 1}
                  aria-label="Disminuir cantidad"
                >
                  −
                </button>
                <span>{line.qty}</span>
                <button
                  type="button"
                  onClick={() => onQty(line.id, line.qty + 1)}
                  aria-label="Aumentar cantidad"
                >
                  +
                </button>
              </div>
              <div className="pos-cart-item__price">{Intl.NumberFormat().format(line.price)}</div>
              <RequirePerm perm={PERMS.POS_DISCOUNT} fallback={null}>
                <button
                  title="Desc."
                  onClick={() => onDiscount(line.id)}
                  className="pos-cart-item__action"
                >
                  %
                </button>
              </RequirePerm>
              <RequirePerm perm={PERMS.POS_PRICE_OVERRIDE} fallback={null}>
                <button
                  title="Precio"
                  onClick={() => onOverridePrice(line.id)}
                  className="pos-cart-item__action"
                >
                  $
                </button>
              </RequirePerm>
              <button
                title="Quitar"
                onClick={() => onRemove(line.id)}
                className="pos-cart-item__action"
              >
                ×
              </button>
            </div>
          ))
        ) : (
          <div className="pos-cart-empty">Vacío</div>
        )}
      </div>
      <hr className="pos-cart-divider" />
      <div className="pos-cart-totals">
        <div className="pos-cart-totals__row">
          <span>Sub-total</span>
          <span>{Intl.NumberFormat().format(totals.sub)}</span>
        </div>
        <div className="pos-cart-totals__row">
          <span>Descuentos</span>
          <span>-{Intl.NumberFormat().format(totals.disc)}</span>
        </div>
        <div className="pos-cart-totals__row">
          <span>Impuestos</span>
          <span>{Intl.NumberFormat().format(totals.tax)}</span>
        </div>
        <div className="pos-cart-totals__row pos-cart-totals__row--grand">
          <span>Total</span>
          <span>{Intl.NumberFormat().format(totals.grand)}</span>
        </div>
      </div>
    </div>
  );
}
