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
    <aside
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: 520,
        background: "#0b1220",
        borderLeft: "1px solid rgba(255, 255, 255, 0.08)",
        display: "flex",
        flexDirection: "column",
        zIndex: 70,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: 12,
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        <strong>{title}</strong>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ padding: 12, overflow: "auto", flex: 1, display: "grid", gap: 12 }}>{children}</div>
    </aside>
  );
}

export default Drawer;
