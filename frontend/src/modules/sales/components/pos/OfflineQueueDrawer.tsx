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
    <aside className="pos-offline-drawer">
      <div className="pos-offline-drawer-header">
        <h3 className="pos-offline-drawer-title">Cola offline</h3>
        <button onClick={onClose} className="pos-offline-drawer-close-btn">
          Cerrar
        </button>
      </div>
      <div className="pos-offline-drawer-list">
        {data.length ? (
          data.map((item) => (
            <div key={item.id} className="pos-offline-drawer-item">
              <div className="pos-offline-drawer-item-header">
                <div>
                  <b className="pos-offline-drawer-item-id">{item.id}</b>
                  <div className="pos-offline-drawer-item-date">
                    {new Date(item.when).toLocaleString()}
                  </div>
                </div>
                <div>{Intl.NumberFormat().format(item.total)}</div>
              </div>
              <div className="pos-offline-drawer-item-status">{item.status}</div>
              <div className="pos-offline-drawer-item-actions">
                <button onClick={() => onRetry?.(item.id)} className="pos-offline-drawer-retry-btn">
                  Reintentar
                </button>
                <button
                  onClick={() => onPurge?.(item.id)}
                  className="pos-offline-drawer-delete-btn"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="pos-offline-drawer-empty">Vacía</div>
        )}
      </div>
      <div className="pos-offline-drawer-footer">
        <button onClick={() => onPurge?.()} className="pos-offline-drawer-purge-btn">
          Vaciar cola
        </button>
      </div>
    </aside>
  );
}
