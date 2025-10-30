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
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "grid", placeItems: "center" }}>
      <div
        style={{
          width: 520,
          background: "#0b1220",
          borderRadius: 12,
          border: "1px solid rgba(255,255,255,0.08)",
          padding: 16,
        }}
      >
        <h3 style={{ marginTop: 0 }}>Cliente rápido</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <input
            placeholder="Nombre *"
            value={name}
            onChange={(event) => setName(event.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          <input
            placeholder="Teléfono"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          <input
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
          <input
            placeholder="DNI/RTN"
            value={docId}
            onChange={(event) => setDocId(event.target.value)}
            style={{ padding: 8, borderRadius: 8 }}
          />
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <button onClick={onClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          <button
            disabled={!valid}
            onClick={() => onSubmit?.({ name, phone, email, docId })}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
          >
            Crear
          </button>
        </div>
      </div>
    </div>
  );
}
