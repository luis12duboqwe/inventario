import React from "react";

type Props = {
  onToggleHold?: () => void;
  onOpenPayments?: () => void;
  onClearCart?: () => void;
  onFocusSearch?: () => void;
};

export default function QuickActions({
  onToggleHold,
  onOpenPayments,
  onClearCart,
  onFocusSearch,
}: Props) {
  return (
    <div className="pos-quick-actions">
      <button onClick={onFocusSearch} className="pos-quick-action-btn">
        F1 Buscar
      </button>
      <button onClick={onOpenPayments} className="pos-quick-action-btn-pay">
        F2 Cobrar
      </button>
      <button onClick={onToggleHold} className="pos-quick-action-btn-hold">
        F3 En espera
      </button>
      <button onClick={onClearCart} className="pos-quick-action-btn">
        F4 Limpiar
      </button>
    </div>
  );
}
