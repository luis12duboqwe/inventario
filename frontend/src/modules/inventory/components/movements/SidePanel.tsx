import React from "react";
import type { MovementRow } from "./Table";
import { Button } from "../../../../../components/ui/Button";

type Props = {
  row?: MovementRow | null;
  onClose?: () => void;
};

export default function SidePanel({ row, onClose }: Props) {
  if (!row) return null;
  const fields = [
    ["Fecha", row.date],
    ["Tipo", row.type],
    ["Producto", row.product],
    ["SKU", row.sku || "-"],
    ["Cantidad", String(row.qty)],
    ["De", row.fromStore || "-"],
    ["A", row.toStore || "-"],
    ["Referencia", row.reference || "-"],
    ["Usuario", row.user || "-"],
    ["Nota", row.note || "-"],
  ];
  return (
    <aside className="fixed right-0 top-0 bottom-0 w-[420px] bg-surface border-l border-border p-4 overflow-auto z-40">
      <div className="flex justify-between items-center mb-2">
        <h3 className="m-0 text-lg font-bold">Detalle movimiento</h3>
        <Button variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
      </div>
      <div className="grid gap-2">
        {fields.map(([k, v]) => (
          <div
            key={k}
            className="flex justify-between border-b border-dashed border-border py-1.5 last:border-0"
          >
            <span className="text-muted-foreground">{k}</span>
            <span>{v as string}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
