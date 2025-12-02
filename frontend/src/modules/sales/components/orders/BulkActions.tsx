import React from "react";

type Props = {
  selectedCount: number;
  onExport?: () => void;
  onEmail?: () => void;
  onCancel?: () => void;
  onRefund?: () => void;
};

function BulkActions({ selectedCount, onExport, onEmail, onCancel, onRefund }: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div className="orders-bulk-actions">
      <div className="orders-bulk-actions-count">{selectedCount} seleccionadas</div>
      <div className="orders-bulk-actions-group">
        <button
          onClick={onExport}
          className="orders-bulk-actions-btn orders-bulk-actions-btn--export"
        >
          Exportar
        </button>
        <button
          onClick={onEmail}
          className="orders-bulk-actions-btn orders-bulk-actions-btn--email"
        >
          Enviar factura
        </button>
        <button
          onClick={onCancel}
          className="orders-bulk-actions-btn orders-bulk-actions-btn--cancel"
        >
          Cancelar
        </button>
        <button
          onClick={onRefund}
          className="orders-bulk-actions-btn orders-bulk-actions-btn--refund"
        >
          Reembolsar
        </button>
      </div>
    </div>
  );
}

export default BulkActions;
