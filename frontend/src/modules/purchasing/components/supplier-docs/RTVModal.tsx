import React, { useState } from "react";

type RTVReason = "DEFECT" | "WRONG_ITEM" | "OVER_SHIPMENT" | "OTHER";

type Line = {
  id: string;
  description: string;
  reason: RTVReason;
  qty: number;
};

type Props = {
  open?: boolean;
  poId?: string;
  onClose?: () => void;
  onSubmit?: (dto: { poId?: string; lines: Line[] }) => void;
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
  width: 640,
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

const reasons: { label: string; value: RTVReason }[] = [
  { label: "Defecto", value: "DEFECT" },
  { label: "Producto incorrecto", value: "WRONG_ITEM" },
  { label: "Exceso", value: "OVER_SHIPMENT" },
  { label: "Otro", value: "OTHER" },
];

export default function RTVModal({ open, poId, onClose, onSubmit }: Props) {
  const [lines, setLines] = useState<Line[]>([]);

  if (!open) {
    return null;
  }

  const addLine = () => {
    setLines((prev) => [
      ...prev,
      { id: `${Date.now()}-${prev.length}`, description: "", reason: "DEFECT", qty: 1 },
    ]);
  };

  const updateLine = (id: string, patch: Partial<Line>) => {
    setLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const removeLine = (id: string) => {
    setLines((prev) => prev.filter((line) => line.id !== id));
  };

  const valid =
    lines.length > 0 &&
    lines.every((line) => line.qty > 0 && Boolean(line.description.trim()));

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0 }}>Devolución a proveedor {poId ? `(#${poId})` : ""}</h3>
        <div style={{ display: "grid", gap: 8 }}>
          {lines.map((line) => (
            <div
              key={line.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 100px 40px",
                gap: 8,
                alignItems: "center",
              }}
            >
              <input
                placeholder="SKU/Producto"
                value={line.description}
                onChange={(event) => updateLine(line.id, { description: event.target.value })}
                style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
              />
              <select
                value={line.reason}
                onChange={(event) => updateLine(line.id, { reason: event.target.value as RTVReason })}
                style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
              >
                {reasons.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                value={line.qty}
                onChange={(event) => updateLine(line.id, { qty: Number(event.target.value || 0) })}
                style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
              />
              <button
                type="button"
                onClick={() => removeLine(line.id)}
                style={{ padding: "6px 8px", borderRadius: 8 }}
              >
                ×
              </button>
            </div>
          ))}
          <button type="button" onClick={addLine} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Agregar línea
          </button>
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
              const payload = { lines } as { lines: Line[]; poId?: string };
              if (poId) {
                payload.poId = poId;
              }
              onSubmit?.(payload);
            }}
            style={{
              ...buttonStyle,
              background: valid ? "#ef4444" : "rgba(239, 68, 68, 0.2)",
              color: "#fff",
              border: valid ? "0" : buttonStyle.border,
              cursor: valid ? "pointer" : "not-allowed",
            }}
          >
            Generar devolución
          </button>
        </div>
      </div>
    </div>
  );
}
