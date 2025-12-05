import React from "react";
import StatusBadge from "./StatusBadge";

export type MoveRow = {
  id: string;
  number?: string;
  date: string;
  type: "IN" | "OUT" | "TRANSFER" | "ADJUST";
  source?: string;
  dest?: string;
  itemsCount: number;
  user?: string;
  status: "DRAFT" | "PENDING" | "APPROVED" | "PARTIAL" | "DONE" | "CANCELLED";
};

type Props = {
  rows?: MoveRow[];
  loading?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onRowClick?: (row: MoveRow) => void;
};

export default function Table({
  rows,
  loading,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onRowClick,
}: Props) {
  const data = Array.isArray(rows) ? rows : [];
  const selected = Array.isArray(selectedIds) ? selectedIds : [];
  const allSelected = data.length > 0 && data.every((row) => selected.includes(row.id));

  if (loading) {
    return <div className="p-4 text-center text-muted-foreground">Cargando…</div>;
  }

  if (!data.length) {
    return <div className="p-4 text-center text-muted-foreground">Sin resultados</div>;
  }

  return (
    <div className="overflow-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-surface-highlight">
            <th className="text-center p-3 w-9">
              <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} />
            </th>
            <th className="text-left p-3 font-medium text-muted-foreground">Fecha</th>
            <th className="text-left p-3 font-medium text-muted-foreground">#</th>
            <th className="text-left p-3 font-medium text-muted-foreground">Tipo</th>
            <th className="text-left p-3 font-medium text-muted-foreground">Origen → Destino</th>
            <th className="text-center p-3 font-medium text-muted-foreground">Items</th>
            <th className="text-left p-3 font-medium text-muted-foreground">Usuario</th>
            <th className="text-left p-3 font-medium text-muted-foreground">Estado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={`border-t border-border hover:bg-surface-highlight transition-colors ${
                onRowClick ? "cursor-pointer" : ""
              }`}
            >
              <td className="text-center p-3" onClick={(event) => event.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selected.includes(row.id)}
                  onChange={() => onToggleSelect?.(row.id)}
                />
              </td>
              <td className="p-3">{row.date}</td>
              <td className="p-3">{row.number || "-"}</td>
              <td className="p-3">{row.type}</td>
              <td className="p-3">{[row.source || "—", row.dest || "—"].join(" → ")}</td>
              <td className="p-3 text-center">{row.itemsCount}</td>
              <td className="p-3">{row.user || "—"}</td>
              <td className="p-3">
                <StatusBadge value={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
