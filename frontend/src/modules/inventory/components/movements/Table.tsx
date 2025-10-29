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

export default function Table({ rows, loading, selectedIds, onToggleSelect, onToggleSelectAll, onRowClick }: Props) {
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
            <th style={{ textAlign: "left", padding: 10 }}>Fecha</th>
            <th style={{ textAlign: "left", padding: 10 }}>Tipo</th>
            <th style={{ textAlign: "left", padding: 10 }}>Producto</th>
            <th style={{ textAlign: "right", padding: 10 }}>Cant.</th>
            <th style={{ textAlign: "left", padding: 10 }}>De</th>
            <th style={{ textAlign: "left", padding: 10 }}>A</th>
            <th style={{ textAlign: "left", padding: 10 }}>Ref.</th>
            <th style={{ textAlign: "left", padding: 10 }}>Usuario</th>
          </tr>
        </thead>
        <tbody>
          {data.map((r) => (
            <tr key={r.id} onClick={() => onRowClick?.(r)} style={{ cursor: onRowClick ? "pointer" : "default" }}>
              <td style={{ textAlign: "center", padding: 10 }} onClick={(e) => e.stopPropagation()}>
                <input type="checkbox" checked={selected.includes(r.id)} onChange={() => onToggleSelect?.(r.id)} />
              </td>
              <td style={{ padding: 10 }}>{r.date}</td>
              <td style={{ padding: 10 }}>{r.type}</td>
              <td style={{ padding: 10 }}>
                {r.product}
                {r.sku ? ` (${r.sku})` : ""}
              </td>
              <td style={{ padding: 10, textAlign: "right" }}>{r.qty}</td>
              <td style={{ padding: 10 }}>{r.fromStore || "-"}</td>
              <td style={{ padding: 10 }}>{r.toStore || "-"}</td>
              <td style={{ padding: 10 }}>{r.reference || "-"}</td>
              <td style={{ padding: 10 }}>{r.user || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
