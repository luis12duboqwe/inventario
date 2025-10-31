import { useState } from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { carrier: string; tracking: string }) => void;
};

function ShipModal({ open, onClose, onSubmit }: Props) {
  const [carrier, setCarrier] = useState<string>("");
  const [tracking, setTracking] = useState<string>("");

  const valid = Boolean(open && carrier.trim());

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <header className="modal-card__header">
          <h3>Enviar transferencia</h3>
        </header>
        <div className="modal-card__body">
          <label>
            <span>Transportista</span>
            <input value={carrier} onChange={(event) => setCarrier(event.target.value)} placeholder="Empresa de envío" />
          </label>
          <label>
            <span>Guía / Tracking</span>
            <input value={tracking} onChange={(event) => setTracking(event.target.value)} placeholder="Opcional" />
          </label>
        </div>
        <footer className="modal-card__footer">
          <button type="button" className="ghost" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="primary"
            disabled={!valid}
            onClick={() => onSubmit?.({ carrier: carrier.trim(), tracking: tracking.trim() })}
          >
            Enviar
          </button>
        </footer>
      </div>
    </div>
  );
}

export default ShipModal;
