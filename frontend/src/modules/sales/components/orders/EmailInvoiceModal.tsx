import React from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

function EmailInvoiceModal({ open, onClose }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div className="orders-email-modal-overlay">
      <div className="orders-email-modal-content">
        <h3 className="orders-email-modal-title">Enviar facturas por email</h3>
        <input placeholder="Para (email)" className="orders-email-modal-input" />
        <div className="orders-email-modal-actions">
          <button onClick={onClose} className="orders-email-modal-btn">
            Cerrar
          </button>
          <button className="orders-email-modal-btn orders-email-modal-btn--send">Enviar</button>
        </div>
      </div>
    </div>
  );
}

export default EmailInvoiceModal;
