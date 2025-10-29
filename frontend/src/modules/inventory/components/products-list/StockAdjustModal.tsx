import React from "react";

import type { ProductRow } from "./Table";

type Props = {
  open?: boolean;
  items?: ProductRow[];
  onClose?: () => void;
  onConfirm?: (delta: number) => void;
};

export default function StockAdjustModal({ open, items, onClose, onConfirm }: Props) {
  const [value, setValue] = React.useState<string>("");
  const selection = Array.isArray(items) ? items : [];
  const count = selection.length;

  React.useEffect(() => {
    if (open) {
      setValue("");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  let summaryLabel = "Selecciona al menos un producto en la tabla para ajustar su inventario.";
  if (count === 1) {
    summaryLabel = `Aplicarás el ajuste a "${selection[0].name}" (stock actual: ${selection[0].stock}).`;
  } else if (count > 1) {
    const [first] = selection;
    summaryLabel = `Aplicarás el ajuste a ${count} productos comenzando por "${first.name}".`;
  }

  const handleConfirm = () => {
    const delta = Number(value);
    if (!Number.isNaN(delta) && delta !== 0 && count > 0) {
      onConfirm?.(delta);
    }
  };

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
          width: 420,
          maxWidth: "95vw",
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Ajustar stock</h3>
        <p style={{ marginTop: 0, marginBottom: 12, color: "#cbd5f5" }}>{summaryLabel}</p>
        <input
          type="number"
          placeholder="Δ Cantidad (ej. +5 o -3)"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          style={{ padding: 8, borderRadius: 8, width: "100%" }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
}
