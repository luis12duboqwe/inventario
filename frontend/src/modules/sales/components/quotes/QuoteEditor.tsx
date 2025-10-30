import React from "react";

type Line = {
  id: string;
  name: string;
  qty: number;
  price: number;
};

type Value = {
  customer?: string;
  note?: string;
  lines: Line[];
};

type Props = {
  value: Value;
  onChange: (next: Value) => void;
  onAddLine?: () => void;
};

export default function QuoteEditor({ value, onChange, onAddLine }: Props) {
  const current = value ?? { lines: [] };
  const lines = Array.isArray(current.lines) ? current.lines : [];

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <input
        placeholder="Cliente"
        value={current.customer ?? ""}
        onChange={(event) => onChange({ ...current, customer: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <textarea
        placeholder="Notas"
        value={current.note ?? ""}
        onChange={(event) => onChange({ ...current, note: event.target.value })}
        style={{ padding: 8, borderRadius: 8, minHeight: 80 }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: 700 }}>Líneas</div>
        <button onClick={onAddLine} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Agregar
        </button>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {lines.map((line) => (
          <div
            key={line.id}
            style={{ display: "grid", gridTemplateColumns: "1fr 100px 120px", gap: 8 }}
          >
            <input
              placeholder="Producto"
              value={line.name}
              onChange={(event) =>
                onChange({
                  ...current,
                  lines: lines.map((item) =>
                    item.id === line.id ? { ...item, name: event.target.value } : item,
                  ),
                })
              }
              style={{ padding: 8, borderRadius: 8 }}
            />
            <input
              type="number"
              value={line.qty}
              onChange={(event) =>
                onChange({
                  ...current,
                  lines: lines.map((item) =>
                    item.id === line.id
                      ? { ...item, qty: Number(event.target.value ?? 0) }
                      : item,
                  ),
                })
              }
              style={{ padding: 8, borderRadius: 8 }}
            />
            <input
              type="number"
              value={line.price}
              onChange={(event) =>
                onChange({
                  ...current,
                  lines: lines.map((item) =>
                    item.id === line.id
                      ? { ...item, price: Number(event.target.value ?? 0) }
                      : item,
                  ),
                })
              }
              style={{ padding: 8, borderRadius: 8 }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
