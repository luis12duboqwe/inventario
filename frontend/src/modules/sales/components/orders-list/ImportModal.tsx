import React from "react";

export type OrdersImportModalProps = {
  open?: boolean;
  onClose?: () => void;
};

function ImportModal({ open, onClose }: OrdersImportModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="orders-list-import-modal-overlay">
      <div className="orders-list-import-modal-content">
        <h3 className="orders-list-import-modal-title">Importar pedidos (CSV/XLSX)</h3>
        <input type="file" accept=".csv,.xlsx" className="orders-list-import-modal-input" />
        <div className="orders-list-import-modal-actions">
          <button onClick={onClose} className="orders-list-import-modal-btn">
            Cancelar
          </button>
          <button
            className="orders-list-import-modal-btn orders-list-import-modal-btn-primary"
            type="button"
          >
            Subir
          </button>
        </div>
      </div>
    </div>
  );
}

export default ImportModal;
