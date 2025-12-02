import React from "react";

const formatter = new Intl.NumberFormat("es-HN", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 2,
});

type Props = {
  subtotal: number;
  discountTotal: number;
  taxTotal: number;
  grandTotal: number;
  onCharge?: () => void;
  onHold?: () => void;
  onClear?: () => void;
};

function Item({ label, value, strong }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={`pos-totals-item ${strong ? "pos-totals-item-strong" : ""}`}>
      <span className={strong ? "pos-totals-label-strong" : "pos-totals-label"}>{label}</span>
      <span>{formatter.format(value || 0)}</span>
    </div>
  );
}

export default function Totals({
  subtotal,
  discountTotal,
  taxTotal,
  grandTotal,
  onCharge,
  onHold,
  onClear,
}: Props) {
  return (
    <div className="pos-totals">
      <Item label="Subtotal" value={subtotal} />
      <Item label="Descuento" value={-Math.abs(discountTotal)} />
      <Item label="Impuestos" value={taxTotal} />
      <Item label="Total" value={grandTotal} strong />
      <div className="pos-totals-actions">
        <button onClick={onClear} className="pos-totals-btn">
          Limpiar
        </button>
        <button onClick={onHold} className="pos-totals-btn-hold">
          En espera
        </button>
        <button onClick={onCharge} className="pos-totals-btn-charge">
          Cobrar
        </button>
      </div>
    </div>
  );
}
