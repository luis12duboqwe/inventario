import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

function ExportModal({ open, onClose }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div className="orders-export-modal-overlay">
      <div className="orders-export-modal-content">
        <h3 className="orders-export-modal-title">Exportar órdenes</h3>
        <div className="orders-export-modal-actions">
          <button onClick={onClose} className="orders-export-modal-btn">
            Cerrar
          </button>
          <button className="orders-export-modal-btn orders-export-modal-btn--export">
            Exportar
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExportModal;
