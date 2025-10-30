import { FormEvent, useState } from "react";

import type { PosSaleItemRequest } from "../../../../services/api/pos";

export type CartLine = PosSaleItemRequest & {
  id: string;
  description?: string;
};

type CartTableProps = {
  items: CartLine[];
  onAdd: (item: Omit<CartLine, "id">) => void;
  onUpdate: (id: string, update: Partial<CartLine>) => void;
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
              setDraft((prev) => ({ ...prev, productId: value, device_id: value }));
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
              setDraft((prev) => ({ ...prev, price: event.target.value ? Number(event.target.value) : undefined }))
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
              setDraft((prev) => ({ ...prev, discount: event.target.value ? Number(event.target.value) : undefined }))
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
                        onChange={(event) =>
                          onUpdate(item.id, {
                            productId: event.target.value ? Number(event.target.value) : undefined,
                            device_id: event.target.value ? Number(event.target.value) : undefined,
                          })
                        }
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
                        onChange={(event) =>
                          onUpdate(item.id, {
                            price: event.target.value ? Number(event.target.value) : undefined,
                          })
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        step="0.1"
                        value={item.discount ?? ""}
                        onChange={(event) =>
                          onUpdate(item.id, {
                            discount: event.target.value ? Number(event.target.value) : undefined,
                          })
                        }
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

