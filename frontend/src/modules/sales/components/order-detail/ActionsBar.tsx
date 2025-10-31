import React from "react";

export type OrderActionsBarProps = {
  onPrint?: () => void;
  onPDF?: () => void;
  onMarkPaid?: () => void;
  onRefund?: () => void;
  onCancel?: () => void;
};

function ActionsBar({ onPrint, onPDF, onMarkPaid, onRefund, onCancel }: OrderActionsBarProps) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button
        onClick={onMarkPaid}
        style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0 }}
      >
        Marcar pagado
      </button>
      <button onClick={onRefund} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Reembolsar
      </button>
      <button
        onClick={onCancel}
        style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
      >
        Cancelar
      </button>
      <button onClick={onPrint} style={{ padding: "8px 12px", borderRadius: 8 }}>
        Imprimir
      </button>
      <button onClick={onPDF} style={{ padding: "8px 12px", borderRadius: 8 }}>
        PDF
      </button>
    </div>
  );
}

export default ActionsBar;
