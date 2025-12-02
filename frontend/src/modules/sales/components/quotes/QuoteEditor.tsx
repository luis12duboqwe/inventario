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
    <div className="quote-editor-container">
      <input
        placeholder="Cliente"
        value={current.customer ?? ""}
        onChange={(event) => onChange({ ...current, customer: event.target.value })}
        className="quote-editor-input"
      />
      <textarea
        placeholder="Notas"
        value={current.note ?? ""}
        onChange={(event) => onChange({ ...current, note: event.target.value })}
        className="quote-editor-textarea"
      />
      <div className="quote-editor-header">
        <div className="quote-editor-title">Líneas</div>
        <button onClick={onAddLine} className="quote-editor-button">
          Agregar
        </button>
      </div>
      <div className="quote-editor-lines">
        {lines.map((line) => (
          <div key={line.id} className="quote-editor-line-row">
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
              className="quote-editor-input"
            />
            <input
              type="number"
              value={line.qty}
              onChange={(event) =>
                onChange({
                  ...current,
                  lines: lines.map((item) =>
                    item.id === line.id ? { ...item, qty: Number(event.target.value ?? 0) } : item,
                  ),
                })
              }
              className="quote-editor-input"
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
              className="quote-editor-input"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
