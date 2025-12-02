import React from "react";

export type OrdersBulkActionsProps = {
  selectedCount: number;
  onMarkPaid?: () => void;
  onCancel?: () => void;
  onExport?: () => void;
  onPrint?: () => void;
  onImport?: () => void;
};

function BulkActions({
  selectedCount,
  onMarkPaid,
  onCancel,
  onExport,
  onPrint,
  onImport,
}: OrdersBulkActionsProps) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div className="orders-list-bulk-actions">
      <span className="orders-list-bulk-count">{selectedCount} seleccionados</span>
      <div className="orders-list-bulk-group">
        <button onClick={onMarkPaid} className="orders-list-bulk-btn orders-list-bulk-btn-success">
          Marcar pagado
        </button>
        <button onClick={onCancel} className="orders-list-bulk-btn orders-list-bulk-btn-danger">
          Cancelar
        </button>
        <button onClick={onImport} className="orders-list-bulk-btn">
          Importar
        </button>
        <button onClick={onExport} className="orders-list-bulk-btn orders-list-bulk-btn-default">
          Exportar
        </button>
        <button onClick={onPrint} className="orders-list-bulk-btn">
          Imprimir
        </button>
      </div>
    </div>
  );
}

export default BulkActions;
