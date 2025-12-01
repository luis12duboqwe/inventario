import React, { useMemo, useState } from "react";

type Props = {
  open?: boolean;
  poId?: string;
  onClose?: () => void;
  onSubmit?: (dto: { poId?: string; freight: number; insurance: number; customs: number }) => void;
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

export default function LandedCostModal({ open, poId, onClose, onSubmit }: Props) {
  const [freight, setFreight] = useState<number>(0);
  const [insurance, setInsurance] = useState<number>(0);
  const [customs, setCustoms] = useState<number>(0);

  const total = useMemo(() => (freight || 0) + (insurance || 0) + (customs || 0), [freight, insurance, customs]);

  if (!open) {
    return null;
  }

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0 }}>Costeo/Landed costs {poId ? `(#${poId})` : ""}</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <label style={{ display: "grid", gap: 4 }}>
            Flete
            <input
              type="number"
              value={freight}
              onChange={(event) => setFreight(Number(event.target.value || 0))}
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            Seguro
            <input
              type="number"
              value={insurance}
              onChange={(event) => setInsurance(Number(event.target.value || 0))}
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            Aduana
            <input
              type="number"
              value={customs}
              onChange={(event) => setCustoms(Number(event.target.value || 0))}
              style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
            />
          </label>
          <div style={{ textAlign: "right", fontWeight: 700 }}>
            Total a prorratear: {Intl.NumberFormat().format(total)}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button type="button" onClick={onClose} style={buttonStyle}>
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => {
              const payload = { freight, insurance, customs } as {
                freight: number;
                insurance: number;
                customs: number;
                poId?: string;
              };
              if (poId) {
                payload.poId = poId;
              }
              onSubmit?.(payload);
            }}
            style={{ ...buttonStyle, background: "#2563eb", color: "#fff", border: "0" }}
          >
            Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}
