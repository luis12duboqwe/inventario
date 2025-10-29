import React from "react";

type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "MIXED";

type Props = {
  open?: boolean;
  amount: number;
  onClose?: () => void;
  onSubmit?: (payload: { method: PaymentMethod; paid: number; note?: string }) => void;
};

const formatter = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 2,
});

export default function PaymentsModal({ open, amount, onClose, onSubmit }: Props) {
  const [method, setMethod] = React.useState<PaymentMethod>("CASH");
  const [paid, setPaid] = React.useState<string>("");
  const [note, setNote] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setPaid("");
      setNote("");
      setMethod("CASH");
    }
  }, [open]);

  if (!open) return null;
  const paidNum = paid ? Number(paid) : NaN;
  const valid = !Number.isNaN(paidNum) && paidNum >= 0;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "grid",
        placeItems: "center",
        zIndex: 50,
      }}
    >
      <div
        style={{
          width: 520,
          maxWidth: "95vw",
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>
          Cobrar — Total {formatter.format(amount)}
        </h3>
        <div style={{ display: "grid", gap: 8 }}>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as PaymentMethod)}
            style={{ padding: 8, borderRadius: 8 }}
          >
            <option value="CASH">Efectivo</option>
            <option value="CARD">Tarjeta</option>
            <option value="TRANSFER">Transferencia</option>
            <option value="MIXED">Mixto</option>
          </select>
          <input
            type="number"
            placeholder="Monto pagado"
            value={paid}
            onChange={(e) => setPaid(e.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
            min={0}
          />
          <input
            placeholder="Nota (opcional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() =>
              valid &&
              onSubmit?.({
                method,
                paid: Number(paidNum),
                note: note.trim() || undefined,
              })
            }
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: valid ? "#22c55e" : "rgba(255,255,255,0.08)",
              color: valid ? "#0b1220" : "#e5e7eb",
              border: 0,
              fontWeight: 700,
            }}
          >
            Confirmar pago
          </button>
        </div>
      </div>
    </div>
  );
}
