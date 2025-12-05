import React from "react";
import { Button } from "@components/ui/Button";
import type { ProductRow } from "./Table";

type Props = {
  row?: ProductRow | null;
  onClose?: () => void;
};

export default function SidePanel({ row, onClose }: Props) {
  if (!row) return null;
  const fields = [
    ["SKU", row.sku],
    ["Nombre", row.name],
    ["Marca", row.brand || "-"],
    ["Categoría", row.category || "-"],
    ["Sucursal", row.store || "-"],
    ["Stock", String(row.stock)],
    ["Precio", String(row.price)],
    ["Estado", row.status || "-"],
  ];
  return (
    <aside className="fixed right-0 top-0 bottom-0 w-[420px] bg-surface border-l border-border p-4 overflow-auto z-40 shadow-xl">
      <div className="flex justify-between items-center mb-4">
        <h3 className="m-0 text-lg font-semibold">Detalle producto</h3>
        <Button variant="ghost" onClick={onClose}>
          Cerrar
        </Button>
      </div>
      <div className="space-y-2">
        {fields.map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-dashed border-border py-2">
            <span className="text-muted-foreground">{k}</span>
            <span>{v as string}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
