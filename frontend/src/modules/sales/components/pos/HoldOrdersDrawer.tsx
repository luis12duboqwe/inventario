import React from "react";

export type HoldOrder = {
  id: string;
  createdAt: string;
  customerName?: string;
  total: number;
};

type Props = {
  open?: boolean;
  items?: HoldOrder[];
  onClose?: () => void;
  onResume?: (id: string) => void;
  onDelete?: (id: string) => void;
};

const formatter = new Intl.NumberFormat("es-HN", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 2,
});

export default function HoldOrdersDrawer({ open, items, onClose, onResume, onDelete }: Props) {
  const data = Array.isArray(items) ? items : [];
  return (
    <aside
      style={{
        position: "fixed",
        top: 0,
        bottom: 0,
        right: 0,
        width: open ? 420 : 0,
        overflow: "hidden",
        transition: "width .2s ease",
        background: "#0b1220",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        zIndex: 40,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12 }}>
        <strong>Ventas en espera</strong>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ display: "grid", gap: 8, padding: 12, overflow: "auto", height: "calc(100% - 48px)" }}>
        {data.length === 0 ? (
          <div style={{ color: "#94a3b8" }}>Sin ventas en espera</div>
        ) : (
          data.map((o) => (
            <div
              key={o.id}
              style={{
                padding: 10,
                borderRadius: 12,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{o.customerName || "Sin cliente"}</div>
                  <div style={{ color: "#94a3b8", fontSize: 12 }}>
                    {new Date(o.createdAt).toLocaleString()}
                  </div>
                </div>
                <div style={{ fontWeight: 700 }}>{formatter.format(o.total)}</div>
              </div>
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
                <button
                  onClick={() => onResume?.(o.id)}
                  style={{ padding: "8px 12px", borderRadius: 8, background: "#2563eb", color: "#fff", border: 0 }}
                >
                  Reanudar
                </button>
                <button onClick={() => onDelete?.(o.id)} style={{ padding: "8px 12px", borderRadius: 8 }}>
                  Eliminar
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
