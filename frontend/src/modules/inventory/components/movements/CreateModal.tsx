import React from "react";
import {
  MOVEMENT_TYPE_OPTIONS,
  type MovementType,
} from "./constants";

export type MovementCreatePayload = {
  type: MovementType;
  productId: string;
  qty: number;
  fromStoreId?: string;
  toStoreId?: string;
  reference?: string;
  note?: string;
};

type Props = {
  open?: boolean;
  onClose?: () => void;
  onCreate?: (payload: MovementCreatePayload) => void;
};

export default function CreateModal({ open, onClose, onCreate }: Props) {
  const [type, setType] = React.useState<MovementType>("entrada");
  const [productId, setProductId] = React.useState("");
  const [qty, setQty] = React.useState<string>("");
  const [fromStoreId, setFromStoreId] = React.useState("");
  const [toStoreId, setToStoreId] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [note, setNote] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setType("entrada");
      setProductId("");
      setQty("");
      setFromStoreId("");
      setToStoreId("");
      setReference("");
      setNote("");
    }
  }, [open]);

  if (!open) return null;
  const validQty = qty ? Number(qty) : NaN;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "grid", placeItems: "center", zIndex: 50 }}>
      <div
        style={{
          width: 560,
          maxWidth: "95vw",
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Nuevo movimiento</h3>
        <div style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(2, minmax(200px,1fr))" }}>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as MovementType)}
            style={{ padding: 8, borderRadius: 8 }}
          >
            {MOVEMENT_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            placeholder="Product ID"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          <input
            type="number"
            placeholder="Cantidad"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          {type !== "entrada" ? (
            <input
              placeholder="Sucursal origen (fromStoreId)"
              value={fromStoreId}
              onChange={(e) => setFromStoreId(e.target.value)}
              style={{ padding: 8, borderRadius: 8 }}
            />
          ) : (
            <div />
          )}
          {type !== "salida" ? (
            <input
              placeholder="Sucursal destino (toStoreId)"
              value={toStoreId}
              onChange={(e) => setToStoreId(e.target.value)}
              style={{ padding: 8, borderRadius: 8 }}
            />
          ) : (
            <div />
          )}
          <input
            placeholder="Referencia (opcional)"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
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
            onClick={() => {
              if (!productId || Number.isNaN(validQty) || validQty === 0) return;
              const payload: MovementCreatePayload = {
                type,
                productId,
                qty: Number(validQty),
                reference,
                note,
              };
              if (type !== "entrada") {
                payload.fromStoreId = fromStoreId;
              }
              if (type !== "salida") {
                payload.toStoreId = toStoreId;
              }
              onCreate?.(payload);
            }}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
          >
            Crear
          </button>
        </div>
      </div>
    </div>
  );
}
