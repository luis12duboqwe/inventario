import React from "react";

type Discount = { type: "PERCENT" | "AMOUNT"; value: number } | null;

type Line = {
  id: string;
  sku?: string;
  name: string;
  qty: number;
  price: number;
  discount?: Discount;
  imei?: string;
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
    <div
      style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 10 }}
    >
      <div style={{ fontWeight: 700, marginBottom: 8 }}>Carrito</div>
      <div style={{ display: "grid", gap: 8, maxHeight: 360, overflow: "auto" }}>
        {data.length ? (
          data.map((line) => (
            <div
              key={line.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 70px 90px 26px 26px 26px",
                gap: 8,
                alignItems: "center",
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{line.name}</div>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>
                  {line.sku ?? "—"}
                  {line.imei ? ` · IMEI ${line.imei}` : ""}
                </div>
              </div>
              <input
                type="number"
                min={1}
                value={line.qty}
                onChange={(event) =>
                  onQty(line.id, Math.max(1, Number(event.target.value ?? 1)))
                }
                style={{ padding: 6, borderRadius: 8, textAlign: "center" }}
              />
              <div style={{ textAlign: "right" }}>
                {Intl.NumberFormat().format(line.price)}
              </div>
              <button
                title="Desc."
                onClick={() => onDiscount(line.id)}
                style={{ padding: "6px 8px", borderRadius: 8 }}
              >
                %
              </button>
              <button
                title="Precio"
                onClick={() => onOverridePrice(line.id)}
                style={{ padding: "6px 8px", borderRadius: 8 }}
              >
                $
              </button>
              <button
                title="Quitar"
                onClick={() => onRemove(line.id)}
                style={{ padding: "6px 8px", borderRadius: 8 }}
              >
                ×
              </button>
            </div>
          ))
        ) : (
          <div style={{ color: "#9ca3af" }}>Vacío</div>
        )}
      </div>
      <hr style={{ borderColor: "rgba(255,255,255,0.08)", margin: "10px 0" }} />
      <div style={{ display: "grid", gap: 6, fontSize: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Sub-total</span>
          <span>{Intl.NumberFormat().format(totals.sub)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Descuentos</span>
          <span>-{Intl.NumberFormat().format(totals.disc)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Impuestos</span>
          <span>{Intl.NumberFormat().format(totals.tax)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
          <span>Total</span>
          <span>{Intl.NumberFormat().format(totals.grand)}</span>
        </div>
      </div>
    </div>
  );
}
