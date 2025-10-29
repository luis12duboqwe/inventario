import React from "react";

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
    <div style={{ display: "grid", gap: 8 }}>
      <div>
        <button onClick={onAdd} style={{ padding: "8px 12px", borderRadius: 8 }} type="button">
          Agregar ítem
        </button>
      </div>
      <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ background: "rgba(255,255,255,0.03)" }}>
              <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
              <th style={{ textAlign: "left", padding: 10 }}>Producto</th>
              <th style={{ textAlign: "center", padding: 10 }}>Cant.</th>
              <th style={{ textAlign: "right", padding: 10 }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ padding: 12, color: "#9ca3af" }}>
                  Sin items
                </td>
              </tr>
            ) : (
              data.map((row) => (
                <tr key={row.id}>
                  <td style={{ padding: 10 }}>{row.sku}</td>
                  <td style={{ padding: 10 }}>{row.name}</td>
                  <td style={{ padding: 10, textAlign: "center" }}>
                    <input
                      type="number"
                      value={row.qty}
                      onChange={(event) =>
                        onEdit(row.id, { qty: Number(event.target.value || 0) })
                      }
                      style={{ width: 90, padding: 6, borderRadius: 8 }}
                    />
                  </td>
                  <td style={{ padding: 10, textAlign: "right" }}>
                    <button
                      onClick={() => onRemove(row.id)}
                      style={{ padding: "6px 10px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
                      type="button"
                    >
                      Quitar
                    </button>
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
