import React from "react";
import { Button } from "@components/ui/Button";
import { TextField } from "@components/ui/TextField";

type Row = {
  id: string;
  sku: string;
  name: string;
  qty: number;
};

type Props = {
  items: Row[];
  onAdd: () => void;
  onEdit: (id: string, patch: Partial<Row>) => void;
  onRemove: (id: string) => void;
};

export default function StepItems({ items, onAdd, onEdit, onRemove }: Props) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div className="space-y-4">
      <div>
        <Button variant="ghost" onClick={onAdd} type="button">
          Agregar ítem
        </Button>
      </div>
      <div className="overflow-auto rounded-xl border border-border">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-surface-highlight">
              <th className="text-left p-3 font-medium text-muted-foreground">SKU</th>
              <th className="text-left p-3 font-medium text-muted-foreground">Producto</th>
              <th className="text-center p-3 font-medium text-muted-foreground">Cant.</th>
              <th className="text-right p-3 font-medium text-muted-foreground">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-4 text-center text-muted-foreground">
                  Sin items
                </td>
              </tr>
            ) : (
              data.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="p-3">{row.sku}</td>
                  <td className="p-3">{row.name}</td>
                  <td className="p-3 text-center">
                    <TextField
                      type="number"
                      value={String(row.qty)}
                      onChange={(event) => onEdit(row.id, { qty: Number(event.target.value || 0) })}
                      className="w-24 text-center"
                    />
                  </td>
                  <td className="p-3 text-right">
                    <Button
                      variant="danger"
                      onClick={() => onRemove(row.id)}
                      type="button"
                      size="sm"
                    >
                      Quitar
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
