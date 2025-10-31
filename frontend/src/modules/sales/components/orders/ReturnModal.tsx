import React, { useState } from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { amount: number }) => void;
};

function ReturnModal({ open, onClose, onSubmit }: Props) {
  const [amount, setAmount] = useState<string>("");

  if (!open) {
    return null;
  }

  const numericAmount = amount ? Number(amount) : NaN;
  const valid = Number.isFinite(numericAmount) && numericAmount >= 0;

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0, 0, 0, 0.5)", display: "grid", placeItems: "center" }}
    >
      <div
        style={{
          width: 420,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Procesar devolución</h3>
        <input
          type="number"
          placeholder="Monto a devolver"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          style={{ padding: 8, borderRadius: 8, width: "100%" }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() =>
              valid && onSubmit?.({ amount: Number.parseFloat(numericAmount.toFixed(2)) })
            }
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: valid ? "#f59e0b" : "rgba(255, 255, 255, 0.08)",
              color: "#0b1220",
              border: 0,
              opacity: valid ? 1 : 0.4,
            }}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReturnModal;
