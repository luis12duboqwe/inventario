import React, { useState } from "react";
import { QuoteEditor } from "../components/quotes";

type QuoteValue = {
  customer?: string;
  note?: string;
  lines: { id: string; name: string; qty: number; price: number }[];
};

export function QuoteDetailPage() {
  const [value, setValue] = useState<QuoteValue>({ lines: [] });

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <QuoteEditor
        value={value}
        onChange={setValue}
        onAddLine={() =>
          setValue((prev) => ({
            ...prev,
            lines: [
              ...prev.lines,
              { id: String(Date.now()), name: "", qty: 1, price: 0 },
            ],
          }))
        }
      />
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <button
          style={{ padding: "8px 12px", borderRadius: 8 }}
          onClick={() => {
            // TODO(save)
          }}
        >
          Guardar
        </button>
        <button
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
          onClick={() => {
            // TODO(convert->POS)
          }}
        >
          Convertir a venta
        </button>
      </div>
      {/* <PrintQuote business={{ name: "SOFTMOBILE" }} doc={{ number: "Q-0001", date: new Date().toISOString(), customer: "Prueba", lines: value.lines }} /> */}
    </div>
  );
}
