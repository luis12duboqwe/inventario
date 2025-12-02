import React from "react";

export type POSDrawerProps = {
  open?: boolean;
  title?: string;
  onClose?: () => void;
  children?: React.ReactNode;
};

function Drawer({ open, title = "POS", onClose, children }: POSDrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <aside className="pos-drawer">
      <div className="pos-drawer-header">
        <strong>{title}</strong>
        <button onClick={onClose} className="pos-drawer-close">
          Cerrar
        </button>
      </div>
      <div className="pos-drawer-content">{children}</div>
    </aside>
  );
}

export default Drawer;
