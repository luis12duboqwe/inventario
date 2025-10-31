import React from "react";

import POStatusBadge from "../po-list/StatusBadge";

type Props = {
  poNumber?: string;
  status: string;
  onPrint?: () => void;
  onExportPDF?: () => void;
  onReceive?: () => void;
  onCancel?: () => void;
};

export default function Header({
  poNumber,
  status,
  onPrint,
  onExportPDF,
  onReceive,
  onCancel,
}: Props) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Orden de compra</div>
        <h2 style={{ margin: "4px 0 0 0" }}>{poNumber || "—"}</h2>
        <div style={{ marginTop: 6 }}>
          <POStatusBadge value={status} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onPrint} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Imprimir
        </button>
        <button onClick={onExportPDF} style={{ padding: "8px 12px", borderRadius: 8 }}>
          PDF
        </button>
        <button
          onClick={onReceive}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
        >
          Recepcionar
        </button>
        <button
          onClick={onCancel}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
