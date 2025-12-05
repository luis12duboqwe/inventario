import React from "react";

export type ProductRow = {
  id: string;
  sku: string;
  name: string;
  brand?: string;
  category?: string;
  store?: string;
  stock: number;
  minStock?: number;
  price: number;
  status?: string;
};

type Props = {
  rows?: ProductRow[];
  loading?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onRowClick?: (row: ProductRow) => void;
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
            <th className="text-left p-2.5">SKU</th>
            <th className="text-left p-2.5">Nombre</th>
            <th className="text-left p-2.5">Marca</th>
            <th className="text-left p-2.5">Categoría</th>
            <th className="text-left p-2.5">Sucursal</th>
            <th className="text-right p-2.5">Stock</th>
            <th className="text-right p-2.5">Precio</th>
            <th className="text-left p-2.5">Estado</th>
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
              <td className="p-2.5">{r.sku}</td>
              <td className="p-2.5">{r.name}</td>
              <td className="p-2.5">{r.brand || "-"}</td>
              <td className="p-2.5">{r.category || "-"}</td>
              <td className="p-2.5">{r.store || "-"}</td>
              <td className="p-2.5 text-right">{r.stock}</td>
              <td className="p-2.5 text-right">{r.price}</td>
              <td className="p-2.5">{r.status || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
