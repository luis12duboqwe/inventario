import React from "react";

import StatusBadge from "./StatusBadge";
import StockBadge from "./StockBadge";

export type ProductRow = {
  id: string;
  name: string;
  sku?: string;
  price: number;
  status: "ACTIVE" | "INACTIVE";
  stock: number;
  category?: string;
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
  const allSelected = data.length > 0 && data.every((row) => selected.includes(row.id));

  if (loading) {
    return <div style={{ padding: 12 }}>Cargando…</div>;
  }

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin resultados</div>;
  }

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)" }}>
            <th style={{ textAlign: "center", padding: 10, width: 36 }}>
              <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} />
            </th>
            <th style={{ textAlign: "left", padding: 10 }}>Nombre</th>
            <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
            <th style={{ textAlign: "left", padding: 10 }}>Categoría</th>
            <th style={{ textAlign: "right", padding: 10 }}>Precio</th>
            <th style={{ textAlign: "center", padding: 10 }}>Stock</th>
            <th style={{ textAlign: "left", padding: 10 }}>Estado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              style={{ cursor: onRowClick ? "pointer" : "default" }}
            >
              <td style={{ textAlign: "center", padding: 10 }} onClick={(event) => event.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selected.includes(row.id)}
                  onChange={() => onToggleSelect?.(row.id)}
                />
              </td>
              <td style={{ padding: 10 }}>{row.name}</td>
              <td style={{ padding: 10 }}>{row.sku || "—"}</td>
              <td style={{ padding: 10 }}>{row.category || "—"}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{Intl.NumberFormat().format(row.price)}</td>
              <td style={{ padding: 10, textAlign: "center" }}>
                <StockBadge qty={row.stock} />
              </td>
              <td style={{ padding: 10 }}>
                <StatusBadge value={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
