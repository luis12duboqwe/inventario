import React from "react";

export type OrdersExportModalProps = {
  open?: boolean;
  onClose?: () => void;
};

function ExportModal({ open, onClose }: OrdersExportModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="orders-list-export-modal-overlay">
      <div className="orders-list-export-modal-content">
        <h3 className="orders-list-export-modal-title">Exportar pedidos</h3>
        <div className="orders-list-export-modal-actions">
          <button onClick={onClose} className="orders-list-export-modal-btn">
            Cerrar
          </button>
          <button
            className="orders-list-export-modal-btn orders-list-export-modal-btn-primary"
            type="button"
          >
            Exportar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExportModal;
