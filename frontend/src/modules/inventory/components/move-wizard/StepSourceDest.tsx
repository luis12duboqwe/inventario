import React from "react";

type MoveType = "IN" | "OUT" | "TRANSFER" | "ADJUST";

type Props = {
  type: MoveType;
  sourceId?: string;
  destId?: string;
  reason?: string;
  onChange: (patch: Partial<{ sourceId: string; destId: string; reason: string }>) => void;
};

export default function StepSourceDest({ type, sourceId, destId, reason, onChange }: Props) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Origen</div>
        <input
          placeholder="Sucursal origen ID"
          value={sourceId || ""}
          onChange={(event) => onChange({ sourceId: event.target.value })}
          style={{ width: "100%", padding: 8, borderRadius: 8 }}
        />
      </div>
      {type !== "OUT" ? (
        <div>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Destino</div>
          <input
            placeholder="Sucursal destino ID"
            value={destId || ""}
            onChange={(event) => onChange({ destId: event.target.value })}
            style={{ width: "100%", padding: 8, borderRadius: 8 }}
          />
        </div>
      ) : null}
      <div style={{ gridColumn: "1 / -1" }}>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Motivo</div>
        <input
          placeholder="Motivo del movimiento"
          value={reason || ""}
          onChange={(event) => onChange({ reason: event.target.value })}
          style={{ width: "100%", padding: 8, borderRadius: 8 }}
        />
      </div>
    </div>
  );
}
