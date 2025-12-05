import React from "react";

export type MovementRow = {
  id: string;
  date: string;
  type: "IN" | "OUT" | "TRANSFER";
  product: string;
  sku?: string;
  qty: number;
  fromStore?: string;
  toStore?: string;
  user?: string;
  reference?: string;
  note?: string;
};

type Props = {
  rows?: MovementRow[];
  loading?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onRowClick?: (row: MovementRow) => void;
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
  const allSelected = data.length > 0 && data.every((r) => selected.includes(r.id));

  if (loading) return <div className="p-4 text-center text-muted-foreground">Cargando…</div>;
  if (!data.length)
    return <div className="p-4 text-center text-muted-foreground">Sin resultados</div>;

  return (
    <div className="overflow-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-surface-highlight">
            <th className="text-center p-2.5 w-9">
              <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} />
            </th>
            <th className="text-left p-2.5">Fecha</th>
            <th className="text-left p-2.5">Tipo</th>
            <th className="text-left p-2.5">Producto</th>
            <th className="text-right p-2.5">Cant.</th>
            <th className="text-left p-2.5">De</th>
            <th className="text-left p-2.5">A</th>
            <th className="text-left p-2.5">Ref.</th>
            <th className="text-left p-2.5">Usuario</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr
              key={r.id}
              onClick={() => onRowClick?.(r)}
              className={onRowClick ? "cursor-pointer hover:bg-surface-highlight" : ""}
            >
              <td className="text-center p-2.5" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selected.includes(r.id)}
                  onChange={() => onToggleSelect?.(r.id)}
                />
              </td>
              <td className="p-2.5">{r.date}</td>
              <td className="p-2.5">{r.type}</td>
              <td className="p-2.5">
                {r.product}
                {r.sku ? ` (${r.sku})` : ""}
              </td>
              <td className="p-2.5 text-right">{r.qty}</td>
              <td className="p-2.5">{r.fromStore || "-"}</td>
              <td className="p-2.5">{r.toStore || "-"}</td>
              <td className="p-2.5">{r.reference || "-"}</td>
              <td className="p-2.5">{r.user || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
