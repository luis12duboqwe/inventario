import React, { useState } from "react";

type ReturnLine = {
  id: string;
  ticket?: string;
  imei?: string;
  name: string;
  qty: number;
  price: number;
  restock?: boolean;
};

type Payload = {
  lines: ReturnLine[];
  reason: string;
  note?: string;
};

type Props = {
  onSubmit?: (payload: Payload) => void;
};

export default function ReturnEditor({ onSubmit }: Props) {
  const [reason, setReason] = useState<string>("DEFECT");
  const [note, setNote] = useState<string>("");
  const [lines, setLines] = useState<ReturnLine[]>([]);

  const addLine = () => {
    setLines((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        name: "",
        qty: 1,
        price: 0,
        restock: true,
      },
    ]);
  };

  const updateLine = (id: string, payload: Partial<ReturnLine>) => {
    setLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...payload } : line)));
  };

  const removeLine = (id: string) => {
    setLines((prev) => prev.filter((line) => line.id !== id));
  };

  const valid = lines.length > 0 && lines.every((line) => line.qty > 0);

  return (
    <div className="return-editor">
      <select
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        className="return-editor-select"
      >
        <option value="DEFECT">Defecto</option>
        <option value="BUYER_REMORSE">Arrepentimiento</option>
        <option value="WARRANTY">Garantía</option>
        <option value="OTHER">Otro</option>
      </select>
      <textarea
        placeholder="Notas"
        value={note}
        onChange={(event) => setNote(event.target.value)}
        className="return-editor-textarea"
      />
      <div className="return-editor-header">
        <div className="return-editor-title">Ítems</div>
        <button onClick={addLine} className="return-editor-add-btn">
          Agregar
        </button>
      </div>
      <div className="return-editor-lines">
        {lines.map((line) => (
          <div key={line.id} className="return-editor-line">
            <input
              placeholder="#Ticket"
              value={line.ticket ?? ""}
              onChange={(event) => updateLine(line.id, { ticket: event.target.value })}
              className="return-editor-input"
            />
            <input
              placeholder="IMEI/serial"
              value={line.imei ?? ""}
              onChange={(event) => updateLine(line.id, { imei: event.target.value })}
              className="return-editor-input"
            />
            <input
              placeholder="Producto"
              value={line.name}
              onChange={(event) => updateLine(line.id, { name: event.target.value })}
              className="return-editor-input"
            />
            <input
              type="number"
              value={line.qty}
              onChange={(event) => updateLine(line.id, { qty: Number(event.target.value ?? 0) })}
              className="return-editor-input"
            />
            <input
              type="number"
              value={line.price}
              onChange={(event) => updateLine(line.id, { price: Number(event.target.value ?? 0) })}
              className="return-editor-input"
            />
            <label className="return-editor-checkbox-label">
              <input
                type="checkbox"
                checked={!!line.restock}
                onChange={(event) => updateLine(line.id, { restock: event.target.checked })}
              />{" "}
              Reingresar
            </label>
            <button onClick={() => removeLine(line.id)} className="return-editor-remove-btn">
              ×
            </button>
          </div>
        ))}
      </div>
      <div className="return-editor-actions">
        <button
          disabled={!valid}
          onClick={() => onSubmit?.({ lines, reason, note })}
          className="return-editor-submit-btn"
        >
          Generar devolución
        </button>
      </div>
    </div>
  );
}
