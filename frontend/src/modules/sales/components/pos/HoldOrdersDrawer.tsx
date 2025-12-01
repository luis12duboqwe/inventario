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
    <aside className={`pos-drawer ${open ? "pos-drawer-open" : "pos-drawer-closed"}`}>
      <div className="pos-drawer-header">
        <strong>Ventas en espera</strong>
        <button onClick={onClose} className="pos-drawer-close-btn">
          Cerrar
        </button>
      </div>
      <div className="pos-drawer-content">
        {data.length === 0 ? (
          <div className="pos-drawer-empty">Sin ventas en espera</div>
        ) : (
          data.map((o) => (
            <div key={o.id} className="pos-drawer-item">
              <div className="pos-drawer-item-header">
                <div>
                  <div className="pos-drawer-item-title">{o.customerName || "Sin cliente"}</div>
                  <div className="pos-drawer-item-meta">
                    {new Date(o.createdAt).toLocaleString()}
                  </div>
                </div>
                <div className="pos-drawer-item-total">{formatter.format(o.total)}</div>
              </div>
              <div className="pos-drawer-item-actions">
                <button onClick={() => onResume?.(o.id)} className="pos-drawer-resume-btn">
                  Reanudar
                </button>
                <button onClick={() => onDelete?.(o.id)} className="pos-drawer-delete-btn">
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
