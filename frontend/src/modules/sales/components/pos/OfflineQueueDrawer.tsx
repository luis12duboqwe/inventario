import React from "react";

type PendingSale = {
  id: string;
  when: string;
  total: number;
  status: "QUEUED" | "RETRYING" | "FAILED";
};

type Props = {
  open?: boolean;
  items: PendingSale[];
  onClose?: () => void;
  onRetry?: (id: string) => void;
  onPurge?: (id?: string) => void;
};

export default function OfflineQueueDrawer({ open, items, onClose, onRetry, onPurge }: Props) {
  if (!open) {
    return null;
  }

  const data = Array.isArray(items) ? items : [];

  return (
    <aside
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 420,
        background: "#0b1220",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        overflow: "auto",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Cola offline</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
        {data.length ? (
          data.map((item) => (
            <div
              key={item.id}
              style={{
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 10,
                padding: 10,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <b>{item.id}</b>
                  <div style={{ fontSize: 12, color: "#94a3b8" }}>
                    {new Date(item.when).toLocaleString()}
                  </div>
                </div>
                <div>{Intl.NumberFormat().format(item.total)}</div>
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{item.status}</div>
              <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
                <button onClick={() => onRetry?.(item.id)} style={{ padding: "6px 10px", borderRadius: 8 }}>
                  Reintentar
                </button>
                <button
                  onClick={() => onPurge?.(item.id)}
                  style={{ padding: "6px 10px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))
        ) : (
          <div style={{ color: "#9ca3af" }}>Vacía</div>
        )}
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
        <button onClick={() => onPurge?.()} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Vaciar cola
        </button>
      </div>
    </aside>
  );
}
