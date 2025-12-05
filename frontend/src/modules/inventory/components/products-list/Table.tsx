import React from "react";
import StatusBadge from "./StatusBadge";
import StockBadge from "./StockBadge";
import "../../InventoryTable.css"; // Ensure styles are loaded

export type ProductRow = {
  id: string;
  name: string;
  sku?: string;
  price: number;
  status: "ACTIVE" | "INACTIVE";
  stock: number;
  category?: string;
  brand?: string;
  store?: string;
  storeId?: number;
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
    return <div className="p-3">Cargando…</div>;
  }

  if (data.length === 0) {
    return <div className="product-grid__empty">Sin resultados</div>;
  }

  return (
    <div className="overflow-auto">
      <table className="inventory-table">
        <thead>
          <tr>
            <th className="text-center w-9">
              <input type="checkbox" checked={allSelected} onChange={onToggleSelectAll} />
            </th>
            <th>Nombre</th>
            <th>SKU</th>
            <th>Categoría</th>
            <th className="text-right">Precio</th>
            <th className="text-center">Stock</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={`${selected.includes(row.id) ? "selected" : ""} ${
                onRowClick ? "cursor-pointer" : "cursor-default"
              }`}
            >
              <td className="text-center" onClick={(event) => event.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selected.includes(row.id)}
                  onChange={() => onToggleSelect?.(row.id)}
                />
              </td>
              <td>{row.name}</td>
              <td>{row.sku || "—"}</td>
              <td>{row.category || "—"}</td>
              <td className="text-right">
                {Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(
                  row.price,
                )}
              </td>
              <td className="text-center">
                <StockBadge qty={row.stock} />
              </td>
              <td>
                <StatusBadge value={row.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
