import React, { useState } from "react";

type Payload = {
  name: string;
  phone?: string;
  email?: string;
  docId?: string;
};

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: Payload) => void;
};

export default function FastCustomerModal({ open, onClose, onSubmit }: Props) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [docId, setDocId] = useState("");

  if (!open) {
    return null;
  }

  const valid = name.trim().length > 0;

  return (
    <div className="pos-fast-customer-modal-overlay">
      <div className="pos-fast-customer-modal-content">
        <h3 className="pos-fast-customer-modal-title">Cliente rápido</h3>
        <div className="pos-fast-customer-modal-form">
          <input
            placeholder="Nombre *"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="pos-fast-customer-modal-input"
          />
          <input
            placeholder="Teléfono"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="pos-fast-customer-modal-input"
          />
          <input
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="pos-fast-customer-modal-input"
          />
          <input
            placeholder="DNI/RTN"
            value={docId}
            onChange={(event) => setDocId(event.target.value)}
            className="pos-fast-customer-modal-input"
          />
        </div>
        <div className="pos-fast-customer-modal-actions">
          <button onClick={onClose} className="pos-fast-customer-modal-cancel-btn">
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.({ name, phone, email, docId })}
            className="pos-fast-customer-modal-create-btn"
          >
            Crear
          </button>
        </div>
      </div>
    </div>
  );
}
