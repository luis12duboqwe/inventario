import React, { useMemo, useState } from "react";
import SerialCapture from "./SerialCapture";
import PutawayPanel from "./PutawayPanel";

type Line = {
  id: string;
  name: string;
  sku?: string;
  qtyOrdered: number;
  qtyReceived: number;
  allowSerial?: boolean;
};

type Props = {
  open?: boolean;
  poNumber?: string;
  lines?: Line[];
  onClose?: () => void;
  onSubmit?: (dto: { qtys: Record<string, number>; serials: Record<string, string[]> }) => void;
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
  width: 860,
  maxHeight: "90vh",
  overflow: "auto",
  background: "#0b1220",
  borderRadius: 12,
  border: "1px solid rgba(255, 255, 255, 0.08)",
  padding: 16,
  boxShadow: "0 20px 50px rgba(8, 15, 30, 0.75)",
};

const lineStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "2fr 100px 1fr",
  gap: 8,
  alignItems: "center",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: 8,
  padding: 8,
  background: "rgba(15, 23, 42, 0.6)",
};

export default function ReceiveModal({ open, poNumber, lines, onClose, onSubmit }: Props) {
  const data = useMemo(() => (Array.isArray(lines) ? lines : []), [lines]);
  const [qtys, setQtys] = useState<Record<string, number>>({});
  const [serials, setSerials] = useState<Record<string, string[]>>({});

  if (!open) {
    return null;
  }

  const patchQty = (id: string, value: number) => {
    setQtys((prev) => ({ ...prev, [id]: Number.isNaN(value) ? 0 : Math.max(0, value) }));
  };

  const patchSerials = (id: string, arr: string[]) => {
    setSerials((prev) => ({ ...prev, [id]: arr }));
  };

  const isQtyValid = data.every((line) => {
    const currentQty = qtys[line.id] ?? 0;
    const alreadyReceived = line.qtyReceived ?? 0;
    return currentQty + alreadyReceived <= line.qtyOrdered;
  });

  const isSerialsValid = data.every((line) => {
    if (!line.allowSerial) {
      return true;
    }

    const expectedQty = qtys[line.id] ?? 0;
    const capturedSerials = (serials[line.id] ?? []).filter((serial) => serial.trim().length > 0);

    return capturedSerials.length === expectedQty;
  });

  const isValid = isQtyValid && isSerialsValid;

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <h3 style={{ marginTop: 0 }}>
          Recibir PO {poNumber ? `(${poNumber})` : ""}
        </h3>
        <div style={{ display: "grid", gap: 10 }}>
          {data.map((line) => (
            <div key={line.id} style={lineStyle}>
              <div>
                <div style={{ fontWeight: 700 }}>{line.name}</div>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>
                  {line.sku || "—"} · Pedida {line.qtyOrdered} · Recibida {line.qtyReceived}
                </div>
              </div>
              <input
                type="number"
                min={0}
                placeholder="A recibir"
                value={qtys[line.id] ?? 0}
                onChange={(event) => patchQty(line.id, Number(event.target.value || 0))}
                style={{ padding: 8, borderRadius: 8, border: "1px solid rgba(148, 163, 184, 0.4)" }}
              />
              {line.allowSerial ? (
                <SerialCapture value={serials[line.id] ?? []} onChange={(arr) => patchSerials(line.id, arr)} />
              ) : (
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Sin serial</div>
              )}
            </div>
          ))}
          <PutawayPanel />
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button type="button" onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            type="button"
            disabled={!isValid}
            onClick={() => onSubmit?.({ qtys, serials })}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: isValid ? "#22c55e" : "rgba(34, 197, 94, 0.3)",
              color: "#0b1220",
              border: 0,
              cursor: isValid ? "pointer" : "not-allowed",
            }}
          >
            Confirmar recepción
          </button>
        </div>
      </div>
    </div>
  );
}
