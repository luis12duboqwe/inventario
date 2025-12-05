import React from "react";
import { TextField } from "@components/ui/TextField";

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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <TextField
          label="Origen"
          placeholder="Sucursal origen ID"
          value={sourceId || ""}
          onChange={(event) => onChange({ sourceId: event.target.value })}
          fullWidth
        />
      </div>
      {type !== "OUT" ? (
        <div>
          <TextField
            label="Destino"
            placeholder="Sucursal destino ID"
            value={destId || ""}
            onChange={(event) => onChange({ destId: event.target.value })}
            fullWidth
          />
        </div>
      ) : null}
      <div className="col-span-1 md:col-span-2">
        <TextField
          label="Motivo"
          placeholder="Motivo del movimiento"
          value={reason || ""}
          onChange={(event) => onChange({ reason: event.target.value })}
          fullWidth
        />
      </div>
    </div>
  );
}
