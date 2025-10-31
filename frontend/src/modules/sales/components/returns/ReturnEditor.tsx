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
    <div style={{ display: "grid", gap: 10 }}>
      <select
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        style={{ padding: 8, borderRadius: 8 }}
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
        style={{ padding: 8, borderRadius: 8, minHeight: 80 }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: 700 }}>Ítems</div>
        <button onClick={addLine} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Agregar
        </button>
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        {lines.map((line) => (
          <div
            key={line.id}
            style={{
              display: "grid",
              gridTemplateColumns: "140px 160px 1fr 90px 90px 100px 28px",
              gap: 8,
              alignItems: "center",
            }}
          >
            <input
              placeholder="#Ticket"
              value={line.ticket ?? ""}
              onChange={(event) => updateLine(line.id, { ticket: event.target.value })}
              style={{ padding: 8, borderRadius: 8 }}
            />
            <input
              placeholder="IMEI/serial"
              value={line.imei ?? ""}
              onChange={(event) => updateLine(line.id, { imei: event.target.value })}
              style={{ padding: 8, borderRadius: 8 }}
            />
            <input
              placeholder="Producto"
              value={line.name}
              onChange={(event) => updateLine(line.id, { name: event.target.value })}
              style={{ padding: 8, borderRadius: 8 }}
            />
            <input
              type="number"
              value={line.qty}
              onChange={(event) => updateLine(line.id, { qty: Number(event.target.value ?? 0) })}
              style={{ padding: 8, borderRadius: 8 }}
            />
            <input
              type="number"
              value={line.price}
              onChange={(event) => updateLine(line.id, { price: Number(event.target.value ?? 0) })}
              style={{ padding: 8, borderRadius: 8 }}
            />
            <label style={{ fontSize: 12 }}>
              <input
                type="checkbox"
                checked={!!line.restock}
                onChange={(event) => updateLine(line.id, { restock: event.target.checked })}
              />
              {" "}Reingresar
            </label>
            <button onClick={() => removeLine(line.id)} style={{ padding: "6px 8px", borderRadius: 8 }}>
              ×
            </button>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          disabled={!valid}
          onClick={() => onSubmit?.({ lines, reason, note })}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
        >
          Generar devolución
        </button>
      </div>
    </div>
  );
}
