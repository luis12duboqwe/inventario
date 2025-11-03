import React, { useEffect, useMemo, useState } from "react";
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
  loading?: boolean;
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

export default function ReceiveModal({ open, poNumber, lines, onClose, onSubmit, loading = false }: Props) {
  const data = useMemo(() => (Array.isArray(lines) ? lines : []), [lines]);
  const [qtys, setQtys] = useState<Record<string, number>>({});
  const [serials, setSerials] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (!open) {
      return;
    }
    setQtys({});
    setSerials({});
  }, [open, data]);

  if (!open) {
    return null;
  }

  const patchQty = (id: string, value: number) => {
    const normalized = Number.isNaN(value) ? 0 : Math.max(0, Math.floor(value));
    setQtys((prev) => ({ ...prev, [id]: normalized }));
  };

  const patchSerials = (id: string, arr: string[]) => {
    setSerials((prev) => ({ ...prev, [id]: arr }));
  };

  const withinLimits = data.every((line) => {
    const currentQty = qtys[line.id] ?? 0;
    const alreadyReceived = line.qtyReceived ?? 0;
    return currentQty >= 0 && currentQty + alreadyReceived <= line.qtyOrdered;
  });
  const hasQuantities = data.some((line) => (qtys[line.id] ?? 0) > 0);
  const isValid = withinLimits && hasQuantities;

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
        {!withinLimits ? (
          <p style={{ color: "#fca5a5", fontSize: 12 }}>
            Verifica que la cantidad a recibir no exceda lo pendiente en cada línea.
          </p>
        ) : null}
        {withinLimits && !hasQuantities ? (
          <p style={{ color: "#fca5a5", fontSize: 12 }}>
            Indica al menos una línea con unidades a recibir.
          </p>
        ) : null}
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button type="button" onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            type="button"
            disabled={!isValid || loading}
            onClick={() => {
              if (!loading) {
                onSubmit?.({ qtys, serials });
              }
            }}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: isValid && !loading ? "#22c55e" : "rgba(34, 197, 94, 0.3)",
              color: isValid && !loading ? "#0b1220" : "#1f2937",
              border: 0,
              cursor: isValid && !loading ? "pointer" : "not-allowed",
            }}
          >
            {loading ? "Registrando…" : "Confirmar recepción"}
          </button>
        </div>
      </div>
    </div>
  );
}
