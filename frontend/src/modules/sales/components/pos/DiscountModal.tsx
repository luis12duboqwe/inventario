import React, { useState } from "react";

type Payload = {
  type: "PERCENT" | "AMOUNT";
  value: number;
};

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: Payload) => void;
};

export default function DiscountModal({ open, onClose, onSubmit }: Props) {
  const [type, setType] = useState<"PERCENT" | "AMOUNT">("PERCENT");
  const [value, setValue] = useState<number>(0);

  if (!open) {
    return null;
  }

  const valid = Number.isFinite(value) && value >= 0 && (type === "PERCENT" ? value <= 100 : true);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "grid", placeItems: "center" }}>
      <div
        style={{
          width: 420,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Descuento en línea</h3>
        <select
          value={type}
          onChange={(event) => setType(event.target.value as "PERCENT" | "AMOUNT")}
          style={{ padding: 8, borderRadius: 8, width: "100%" }}
        >
          <option value="PERCENT">% Porcentaje</option>
          <option value="AMOUNT">Monto fijo</option>
        </select>
        <input
          type="number"
          value={value}
          onChange={(event) => setValue(Number(event.target.value ?? 0))}
          style={{ padding: 8, borderRadius: 8, width: "100%", marginTop: 8 }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.({ type, value })}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}
