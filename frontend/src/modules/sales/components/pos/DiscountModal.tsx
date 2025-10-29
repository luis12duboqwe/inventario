import React from "react";

type Props = {
  open?: boolean;
  current?: number;
  onClose?: () => void;
  onApply?: (amount: number) => void;
};

export default function DiscountModal({ open, current = 0, onClose, onApply }: Props) {
  const [value, setValue] = React.useState<string>(current ? String(current) : "");

  React.useEffect(() => {
    if (open) {
      setValue(current ? String(current) : "");
    }
  }, [open, current]);

  if (!open) return null;
  const num = value ? Number(value) : NaN;
  const valid = !Number.isNaN(num) && num >= 0;
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
        <h3 style={{ marginTop: 0 }}>Descuento de línea</h3>
        <input
          type="number"
          placeholder="Monto"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          style={{ padding: 8, borderRadius: 8, width: "100%" }}
          min={0}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => valid && onApply?.(Number(num))}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: valid ? "#2563eb" : "rgba(255,255,255,0.08)",
              color: "#fff",
              border: 0,
            }}
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}
