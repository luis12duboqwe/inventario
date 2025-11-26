import { FormEvent, useState } from "react";

import type { PosSaleItemRequest } from "../../../../services/api/pos";

export type CartLine = PosSaleItemRequest & {
  id: string;
  description?: string;
};

const CLEAR_PRODUCT_FIELDS: (keyof CartLine)[] = ["productId", "device_id"];
const CLEAR_PRICE_FIELDS: (keyof CartLine)[] = ["price"];
const CLEAR_DISCOUNT_FIELDS: (keyof CartLine)[] = ["discount"];

type CartTableProps = {
  items: CartLine[];
  onAdd: (item: Omit<CartLine, "id">) => void;
  onUpdate: (id: string, update: Partial<CartLine>, options?: { clear?: ReadonlyArray<keyof CartLine> }) => void;
  onRemove: (id: string) => void;
};

// [PACK34-UI]
export default function CartTable({ items, onAdd, onUpdate, onRemove }: CartTableProps) {
  const [draft, setDraft] = useState<Omit<CartLine, "id">>({ qty: 1 });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.productId && !draft.imei && !draft.device_id) {
      return;
    }
    if (!draft.qty || draft.qty <= 0) {
      return;
    }
    onAdd(draft);
    setDraft({ qty: 1 });
  };

  return (
    <section className="card">
      <header className="card__header">
        <h3 className="card__title">Carrito</h3>
        <p className="card__subtitle">Agrega artículos por SKU/ID o IMEI y ajusta el precio manualmente.</p>
      </header>

      <form className="pos-cart-form" onSubmit={handleSubmit}>
        <label>
          <span>Producto / SKU</span>
          <input
            type="number"
            value={draft.productId ?? draft.device_id ?? ""}
            min={1}
            onChange={(event) => {
              const value = event.target.value ? Number(event.target.value) : undefined;
              setDraft((prev) => {
                const next = { ...prev };
                if (value != null) {
                  next.productId = value;
                  next.device_id = value;
                } else {
                  delete next.productId;
                  delete next.device_id;
                }
                return next;
              });
            }}
            placeholder="ID de producto"
          />
        </label>
        <label>
          <span>IMEI</span>
          <input
            type="text"
            value={draft.imei ?? ""}
            maxLength={18}
            onChange={(event) => setDraft((prev) => ({ ...prev, imei: event.target.value }))}
            placeholder="Escanea IMEI"
          />
        </label>
        <label>
          <span>Cantidad</span>
          <input
            type="number"
            min={1}
            value={draft.qty}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, qty: Number(event.target.value) || 1 }))
            }
            required
          />
        </label>
        <label>
          <span>Precio unitario</span>
          <input
            type="number"
            min={0}
            step="0.01"
            value={draft.price ?? ""}
              onChange={(event) =>
                setDraft((prev) => {
                  const raw = event.target.value;
                  if (raw) {
                    return { ...prev, price: Number(raw) };
                  }
                  const next = { ...prev };
                  delete next.price;
                  return next;
                })
              }
          />
        </label>
        <label>
          <span>Descuento %</span>
          <input
            type="number"
            min={0}
            max={100}
            step="0.1"
            value={draft.discount ?? ""}
              onChange={(event) =>
                setDraft((prev) => {
                  const raw = event.target.value;
                  if (raw) {
                    return { ...prev, discount: Number(raw) };
                  }
                  const next = { ...prev };
                  delete next.discount;
                  return next;
                })
              }
          />
        </label>
        <label className="pos-cart-form__description">
          <span>Descripción</span>
          <input
            type="text"
            value={draft.description ?? ""}
            onChange={(event) => setDraft((prev) => ({ ...prev, description: event.target.value }))}
            placeholder="Descripción breve opcional"
          />
        </label>
        <button type="submit" className="btn btn--primary">
          Agregar
        </button>
      </form>

      <div className="table-wrapper">
        <table className="pos-cart-table">
          <thead>
            <tr>
              <th>Producto</th>
              <th>IMEI</th>
              <th>Cantidad</th>
              <th>Precio</th>
              <th>Descuento %</th>
              <th>Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted-text">
                  Agrega artículos para iniciar la venta POS.
                </td>
              </tr>
            ) : (
              items.map((item) => {
                const unitPrice = Number(item.price ?? 0);
                const quantity = item.qty ?? 1;
                const discountPercent = Number(item.discount ?? 0);
                const lineTotal = unitPrice * quantity * (1 - discountPercent / 100);
                return (
                  <tr key={item.id}>
                    <td>
                      <input
                        type="number"
                        min={1}
                        value={item.productId ?? item.device_id ?? ""}
                        onChange={(event) => {
                          const value = event.target.value ? Number(event.target.value) : null;
                          if (value != null) {
                            onUpdate(item.id, { productId: value, device_id: value });
                          } else {
                            onUpdate(item.id, {}, { clear: CLEAR_PRODUCT_FIELDS });
                          }
                        }}
                      />
                      <small className="muted-text">{item.description ?? "Sin descripción"}</small>
                    </td>
                    <td>
                      <input
                        type="text"
                        value={item.imei ?? ""}
                        onChange={(event) => onUpdate(item.id, { imei: event.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        value={item.qty}
                        onChange={(event) =>
                          onUpdate(item.id, { qty: Number(event.target.value) || 1 })
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        step="0.01"
                        value={item.price ?? ""}
                        onChange={(event) => {
                          const raw = event.target.value;
                          if (raw) {
                            onUpdate(item.id, { price: Number(raw) });
                          } else {
                            onUpdate(item.id, {}, { clear: CLEAR_PRICE_FIELDS });
                          }
                        }}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        step="0.1"
                        value={item.discount ?? ""}
                        onChange={(event) => {
                          const raw = event.target.value;
                          if (raw) {
                            onUpdate(item.id, { discount: Number(raw) });
                          } else {
                            onUpdate(item.id, {}, { clear: CLEAR_DISCOUNT_FIELDS });
                          }
                        }}
                      />
                    </td>
                    <td>${lineTotal.toFixed(2)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn--ghost"
                        onClick={() => onRemove(item.id)}
                      >
                        Quitar
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

