import React, { useState } from "react";

type Props = {
  open?: boolean;
  poId?: string;
  onClose?: () => void;
  onSubmit?: (dto: { poId?: string; number: string; date: string; amount: number; file: File | null }) => void;
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0, 0, 0, 0.5)",
  display: "grid",
  placeItems: "center",
  zIndex: 50,
};

const modalStyle: React.CSSProperties = {
  width: 520,
  background: "#0b1220",
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  padding: 16,
  boxShadow: "0 20px 50px rgba(8, 15, 30, 0.75)",
};

const buttonStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: 8,
  border: "1px solid rgba(59, 130, 246, 0.4)",
  background: "rgba(37, 99, 235, 0.18)",
  color: "#bfdbfe",
};

export default function SupplierInvoiceModal({ open, poId, onClose, onSubmit }: Props) {
  const [number, setNumber] = useState<string>("");
  const [date, setDate] = useState<string>("");
  const [amount, setAmount] = useState<number>(0);
  const [file, setFile] = useState<File | null>(null);

  if (!open) {
    return null;
  }

  const valid = Boolean(number && date && amount > 0);

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0 }}>Factura proveedor {poId ? `(#${poId})` : ""}</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <label style={{ display: "grid", gap: 4 }}>
            Número
            <input
              value={number}
              onChange={(event) => setNumber(event.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            Fecha
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            Monto
            <input
              type="number"
              value={amount}
              min={0}
              onChange={(event) => setAmount(Number(event.target.value || 0))}
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
            />
          </label>
          <input
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
          />
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button type="button" onClick={onClose} style={buttonStyle}>
            Cancelar
          </button>
          <button
            type="button"
            disabled={!valid}
            onClick={() => {
              if (!valid) {
                return;
              }
              const payload = {
                number,
                date,
                amount,
                file,
              } as { number: string; date: string; amount: number; file: File | null; poId?: string };
              if (poId) {
                payload.poId = poId;
              }
              onSubmit?.(payload);
            }}
            style={{
              ...buttonStyle,
              background: valid ? "#2563eb" : "rgba(37, 99, 235, 0.2)",
              color: "#fff",
              border: valid ? "0" : buttonStyle.border,
              cursor: valid ? "pointer" : "not-allowed",
            }}
          >
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}
