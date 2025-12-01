import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onConfirm?: () => void;
};

function CancelModal({ open, onClose, onConfirm }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div className="orders-cancel-modal-overlay">
      <div className="orders-cancel-modal-content">
        <h3 className="orders-cancel-modal-title">Cancelar órdenes</h3>
        <p>¿Seguro que deseas cancelar las órdenes seleccionadas?</p>
        <div className="orders-cancel-modal-actions">
          <button onClick={onClose} className="orders-cancel-modal-btn">
            No
          </button>
          <button
            onClick={onConfirm}
            className="orders-cancel-modal-btn orders-cancel-modal-btn--confirm"
          >
            Sí, cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

export default CancelModal;
