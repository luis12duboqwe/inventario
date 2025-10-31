import React, { useEffect, useMemo, useState } from "react";

type CreditNoteLine = {
  id: string;
  name: string;
  qty: number;
  price: number;
  amount: number;
};

type CreditNotePayload = {
  orderId?: string;
  lines: CreditNoteLine[];
  total: number;
};

type CreditNoteModalProps = {
  open?: boolean;
  orderId?: string;
  onClose?: () => void;
  onSubmit?: (payload: CreditNotePayload) => void;
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function CreditNoteModal({ open, orderId, onClose, onSubmit }: CreditNoteModalProps) {
  const [lines, setLines] = useState<CreditNoteLine[]>([]);

  useEffect(() => {
    if (!open) {
      setLines([]);
    }
  }, [open]);

  const handleAddLine = () => {
    setLines((prev) => [
      ...prev,
      {
        id: `cn-line-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        name: "",
        qty: 1,
        price: 0,
        amount: 0,
      },
    ]);
  };

  const handleLineChange = (id: string, patch: Partial<CreditNoteLine>) => {
    setLines((prev) =>
      prev.map((line) =>
        line.id === id
          ? {
              ...line,
              ...patch,
              qty: Math.max(0, patch.qty ?? line.qty),
              price: Math.max(0, patch.price ?? line.price),
              amount: Math.max(0, patch.amount ?? line.amount),
            }
          : line,
      ),
    );
  };

  const handleRemoveLine = (id: string) => {
    setLines((prev) => prev.filter((line) => line.id !== id));
  };

  const total = useMemo(() => lines.reduce((sum, line) => sum + (line.amount ?? 0), 0), [lines]);

  const isValid = useMemo(
    () => lines.length > 0 && lines.every((line) => line.qty > 0 && line.amount >= 0),
    [lines],
  );

  const handleSubmit = () => {
    if (!isValid) {
      return;
    }
    onSubmit?.({ orderId, lines, total });
  };

  if (!open) {
    return null;
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(8, 15, 35, 0.7)", display: "grid", placeItems: "center", zIndex: 50 }}>
      <div style={{ width: 640, background: "#0b1220", borderRadius: 12, border: "1px solid rgba(37, 99, 235, 0.3)", padding: 16 }}>
        <h3 style={{ marginTop: 0 }}>Nota de crédito {orderId ? `(#${orderId})` : ""}</h3>
        <div style={{ display: "grid", gap: 12 }}>
          {lines.map((line) => (
            <div
              key={line.id}
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 100px 120px 140px 40px",
                gap: 8,
                alignItems: "center",
              }}
            >
              <input
                placeholder="Descripción"
                value={line.name}
                onChange={(event) => handleLineChange(line.id, { name: event.target.value })}
                style={{ padding: 8, borderRadius: 8 }}
              />
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder="Cant"
                value={line.qty}
                onChange={(event) => handleLineChange(line.id, { qty: Number(event.target.value) })}
                style={{ padding: 8, borderRadius: 8 }}
              />
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder="Precio"
                value={line.price}
                onChange={(event) => handleLineChange(line.id, { price: Number(event.target.value) })}
                style={{ padding: 8, borderRadius: 8 }}
              />
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder="Monto"
                value={line.amount}
                onChange={(event) => handleLineChange(line.id, { amount: Number(event.target.value) })}
                style={{ padding: 8, borderRadius: 8 }}
              />
              <button onClick={() => handleRemoveLine(line.id)} style={{ padding: "6px 8px", borderRadius: 8 }}>×</button>
            </div>
          ))}
          <button onClick={handleAddLine} style={{ padding: "8px 12px", borderRadius: 8 }}>Agregar línea</button>
          <div style={{ textAlign: "right", fontWeight: 700 }}>Total NC: {currency.format(Math.max(0, total))}</div>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>Cancelar</button>
          <button
            type="button"
            disabled={!isValid}
            onClick={handleSubmit}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: isValid ? "#2563eb" : "rgba(37, 99, 235, 0.35)",
              color: "#f8fafc",
              border: 0,
              cursor: isValid ? "pointer" : "not-allowed",
            }}
          >
            Emitir NC
          </button>
        </div>
      </div>
    </div>
  );
}

export type { CreditNoteLine, CreditNoteModalProps, CreditNotePayload };
export default CreditNoteModal;
