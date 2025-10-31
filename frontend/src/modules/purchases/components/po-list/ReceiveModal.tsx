import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { qty: number }) => void;
};

export default function ReceiveModal({ open, onClose, onSubmit }: Props) {
  const [qty, setQty] = React.useState<string>("");

  if (!open) {
    return null;
  }

  const num = qty ? Number(qty) : Number.NaN;
  const valid = !Number.isNaN(num) && num > 0;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0, 0, 0, 0.5)", display: "grid", placeItems: "center" }}>
      <div
        style={{
          width: 420,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Recepcionar rápido</h3>
        <input
          type="number"
          placeholder="Cantidad a recepcionar"
          value={qty}
          onChange={(event) => setQty(event.target.value)}
          style={{ padding: 8, borderRadius: 8, width: "100%" }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => valid && onSubmit?.({ qty: Number(num) })}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: valid ? "#22c55e" : "rgba(255, 255, 255, 0.08)",
              color: valid ? "#0b1220" : "#e5e7eb",
              border: 0,
            }}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
