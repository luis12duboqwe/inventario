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
    <aside className="pos-resume-drawer">
      <div className="pos-resume-drawer-header">
        <h3 className="pos-resume-drawer-title">Ventas en espera</h3>
        <button onClick={onClose} className="pos-resume-drawer-close-btn">
          Cerrar
        </button>
      </div>
      <div className="pos-resume-drawer-list">
        {data.length ? (
          data.map((item) => (
            <div key={item.id} className="pos-resume-drawer-item">
              <div className="pos-resume-drawer-item-header">
                <div>
                  <b className="pos-resume-drawer-item-number">{item.number}</b>
                  <div className="pos-resume-drawer-item-date">
                    {new Date(item.date).toLocaleString()}
                  </div>
                </div>
                <div className="pos-resume-drawer-item-total">
                  {Intl.NumberFormat().format(item.total)}
                </div>
              </div>
              <div className="pos-resume-drawer-item-customer">{item.customer ?? "Mostrador"}</div>
              <div className="pos-resume-drawer-item-actions">
                <RequirePerm perm={PERMS.POS_RESUME} fallback={null}>
                  <button
                    onClick={() => onResume?.(item.id)}
                    className="pos-resume-drawer-resume-btn"
                  >
                    Reanudar
                  </button>
                </RequirePerm>
                <button
                  onClick={() => onDelete?.(item.id)}
                  className="pos-resume-drawer-delete-btn"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="pos-resume-drawer-empty">Sin ventas en espera</div>
        )}
      </div>
    </aside>
  );
}
