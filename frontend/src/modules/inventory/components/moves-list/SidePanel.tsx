import React from "react";
import { Button } from "@components/ui/Button";
import StatusBadge from "./StatusBadge";
import type { MoveRow } from "./Table";

type Props = {
  row?: MoveRow | null;
  onClose?: () => void;
};

export default function SidePanel({ row, onClose }: Props) {
  if (!row) {
    return null;
  }

  const fields: Array<[string, string]> = [
    ["Fecha", row.date],
    ["# Mov", row.number || "-"],
    ["Tipo", row.type],
    ["Origen", row.source || "—"],
    ["Destino", row.dest || "—"],
    ["Items", String(row.itemsCount)],
    ["Usuario", row.user || "—"],
  ];

  return (
    <aside className="fixed right-0 top-0 bottom-0 w-[420px] bg-surface border-l border-border p-4 overflow-auto z-40 shadow-xl">
      <div className="flex justify-between items-center mb-4">
        <h3 className="m-0 text-lg font-semibold">Resumen Movimiento</h3>
        <Button variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
      </div>
      <div className="mb-4">
        <StatusBadge value={row.status} />
      </div>
      <div className="space-y-2">
        {fields.map(([label, value]) => (
          <div
            key={label}
            className="flex justify-between border-b border-dashed border-border py-2"
          >
            <span className="text-muted-foreground">{label}</span>
            <span>{value}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
