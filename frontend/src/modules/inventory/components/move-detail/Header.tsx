import React from "react";
import MoveStatusBadge from "../moves-list/StatusBadge";

type Props = {
  number?: string;
  status: string;
  type?: string;
  onPrint?: () => void;
  onExportPDF?: () => void;
  onApprove?: () => void;
  onCancel?: () => void;
};

export default function Header({
  number,
  status,
  type,
  onPrint,
  onExportPDF,
  onApprove,
  onCancel,
}: Props) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Movimiento {type || ""}</div>
        <h2 style={{ margin: "4px 0 0 0" }}>{number || "—"}</h2>
        <div style={{ marginTop: 6 }}>
          <MoveStatusBadge value={status} />
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
          onClick={onApprove}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
        >
          Aprobar
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
