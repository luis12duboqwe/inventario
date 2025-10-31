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

  if (loading) return <div style={{ padding: 12 }}>Cargando…</div>;
  if (!data.length) return <div style={{ padding: 12, color: "#9ca3af" }}>Sin resultados</div>;

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)" }}>
            <th style={{ textAlign: "center", padding: 10, width: 36 }}>
              <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} />
            </th>
            <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
            <th style={{ textAlign: "left", padding: 10 }}>Nombre</th>
            <th style={{ textAlign: "left", padding: 10 }}>Marca</th>
            <th style={{ textAlign: "left", padding: 10 }}>Categoría</th>
            <th style={{ textAlign: "left", padding: 10 }}>Sucursal</th>
            <th style={{ textAlign: "right", padding: 10 }}>Stock</th>
            <th style={{ textAlign: "right", padding: 10 }}>Precio</th>
            <th style={{ textAlign: "left", padding: 10 }}>Estado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr
              key={r.id}
              onClick={() => onRowClick?.(r)}
              style={{ cursor: onRowClick ? "pointer" : "default" }}
            >
              <td style={{ textAlign: "center", padding: 10 }} onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selected.includes(r.id)}
                  onChange={() => onToggleSelect?.(r.id)}
                />
              </td>
              <td style={{ padding: 10 }}>{r.sku}</td>
              <td style={{ padding: 10 }}>{r.name}</td>
              <td style={{ padding: 10 }}>{r.brand || "-"}</td>
              <td style={{ padding: 10 }}>{r.category || "-"}</td>
              <td style={{ padding: 10 }}>{r.store || "-"}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{r.stock}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{r.price}</td>
              <td style={{ padding: 10 }}>{r.status || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
