import React from "react";
// [PACK26-POS-RESUME-PERMS-START]
import { RequirePerm, PERMS } from "../../../../auth/useAuthz";
// [PACK26-POS-RESUME-PERMS-END]

type HoldSale = {
  id: string;
  number: string;
  date: string;
  customer?: string;
  total: number;
};

type Props = {
  open?: boolean;
  items: HoldSale[];
  onClose?: () => void;
  onResume?: (id: string) => void;
  onDelete?: (id: string) => void;
};

export default function HoldResumeDrawer({ open, items, onClose, onResume, onDelete }: Props) {
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
        width: 460,
        background: "#0b1220",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        overflow: "auto",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Ventas en espera</h3>
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
                  <b>{item.number}</b>
                  <div style={{ fontSize: 12, color: "#94a3b8" }}>
                    {new Date(item.date).toLocaleString()}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  {Intl.NumberFormat().format(item.total)}
                </div>
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                {item.customer ?? "Mostrador"}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
                <RequirePerm perm={PERMS.POS_RESUME} fallback={null}>
                  <button onClick={() => onResume?.(item.id)} style={{ padding: "6px 10px", borderRadius: 8 }}>
                    Reanudar
                  </button>
                </RequirePerm>
                <button
                  onClick={() => onDelete?.(item.id)}
                  style={{ padding: "6px 10px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))
        ) : (
          <div style={{ color: "#9ca3af" }}>Sin ventas en espera</div>
        )}
      </div>
    </aside>
  );
}
