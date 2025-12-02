import React from "react";

export type POSActionsProps = {
  onHold?: () => void;
  onResume?: () => void;
  onSaveDraft?: () => void;
  onComplete?: () => void;
  disabled?: boolean;
};

function Actions({ onHold, onResume, onSaveDraft, onComplete, disabled }: POSActionsProps) {
  return (
    <div className="pos-drawer-actions">
      <button onClick={onSaveDraft} className="pos-drawer-btn">
        Guardar borrador
      </button>
      <button onClick={onHold} className="pos-drawer-btn">
        Poner en espera
      </button>
      <button onClick={onResume} className="pos-drawer-btn">
        Recuperar ticket
      </button>
      <button onClick={onComplete} disabled={Boolean(disabled)} className="pos-drawer-btn-complete">
        Completar venta
      </button>
    </div>
  );
}

export default Actions;
