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
    <div className="order-actions-bar">
      <button onClick={onMarkPaid} className="order-actions-btn-primary">
        Marcar pagado
      </button>
      <button onClick={onRefund} className="order-actions-btn">
        Reembolsar
      </button>
      <button onClick={onCancel} className="order-actions-btn-danger">
        Cancelar
      </button>
      <button onClick={onPrint} className="order-actions-btn">
        Imprimir
      </button>
      <button onClick={onPDF} className="order-actions-btn">
        PDF
      </button>
    </div>
  );
}

export default ActionsBar;
