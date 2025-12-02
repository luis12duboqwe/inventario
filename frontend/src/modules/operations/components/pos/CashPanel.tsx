import { FormEvent, useState } from "react";

import type { PosSessionSummary } from "@api/pos";

type StoreOption = {
  id: number;
  name: string;
};

type CashPanelProps = {
  stores: StoreOption[];
  selectedStoreId: number | null;
  onStoreChange: (storeId: number) => void;
  session: PosSessionSummary | null;
  onOpenSession: (payload: { amount: number; notes: string; reason: string }) => Promise<void>;
  onCloseSession: (payload: { amount: number; notes: string; reason: string }) => Promise<void>;
  refreshing: boolean;
  onRefresh: () => void;
  error?: string | null;
};

// [PACK34-UI]
export default function CashPanel({
  stores,
  selectedStoreId,
  onStoreChange,
  session,
  onOpenSession,
  onCloseSession,
  refreshing,
  onRefresh,
  error,
}: CashPanelProps) {
  const [openForm, setOpenForm] = useState({
    amount: 0,
    notes: "",
    reason: "Apertura de caja POS",
  });
  const [closeForm, setCloseForm] = useState({
    amount: 0,
    notes: "",
    reason: "Cierre de caja POS",
  });
  const [loadingAction, setLoadingAction] = useState<"open" | "close" | null>(null);

  const handleOpen = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loadingAction) return;
    setLoadingAction("open");
    try {
      await onOpenSession(openForm);
      setOpenForm({ amount: 0, notes: "", reason: "Apertura de caja POS" });
    } finally {
      setLoadingAction(null);
    }
  };

  const handleClose = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loadingAction) return;
    setLoadingAction("close");
    try {
      await onCloseSession(closeForm);
      setCloseForm({ amount: 0, notes: "", reason: "Cierre de caja POS" });
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <section className="card" data-testid="cash-close">
      <header className="card__header pos-cash-header">
        <div>
          <h3 className="card__title">Caja</h3>
          <p className="card__subtitle">
            Abre o cierra la caja de la sucursal y consulta el estado actual de la sesión.
          </p>
        </div>
        <div className="pos-cash-store-selector">
          <label>
            <span>Sucursal</span>
            <select
              value={selectedStoreId ?? ""}
              onChange={(event) => onStoreChange(Number(event.target.value))}
            >
              <option value="">Selecciona una sucursal</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
      </header>

      {error ? <p className="alert error">{error}</p> : null}

      <div className="pos-cash-status">
        <div>
          <span className="muted-text">Estado</span>
          <strong>{session ? session.status : "Sin sesión"}</strong>
        </div>
        <div>
          <span className="muted-text">Apertura</span>
          <strong>
            {session?.opening_amount != null ? `$${session.opening_amount.toFixed(2)}` : "—"}
          </strong>
        </div>
        <div>
          <span className="muted-text">Esperado</span>
          <strong>
            {session?.expected_amount != null ? `$${session.expected_amount.toFixed(2)}` : "—"}
          </strong>
        </div>
        <div>
          <span className="muted-text">Diferencia</span>
          <strong>
            {session?.difference_amount != null ? `$${session.difference_amount.toFixed(2)}` : "—"}
          </strong>
        </div>
      </div>

      <div className="pos-cash-actions">
        <form onSubmit={handleOpen} className="pos-cash-form">
          <h4>Abrir caja</h4>
          <label>
            <span>Monto inicial</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={openForm.amount}
              onChange={(event) =>
                setOpenForm((prev) => ({ ...prev, amount: Number(event.target.value) }))
              }
              required
            />
          </label>
          <label>
            <span>Notas</span>
            <input
              type="text"
              value={openForm.notes}
              onChange={(event) => setOpenForm((prev) => ({ ...prev, notes: event.target.value }))}
              placeholder="Observaciones opcionales"
            />
          </label>
          <label>
            <span>Motivo corporativo</span>
            <input
              type="text"
              minLength={5}
              value={openForm.reason}
              onChange={(event) => setOpenForm((prev) => ({ ...prev, reason: event.target.value }))}
              required
            />
          </label>
          <button type="submit" className="btn btn--primary" disabled={loadingAction === "open"}>
            {loadingAction === "open" ? "Abriendo…" : "Abrir caja"}
          </button>
        </form>

        <form onSubmit={handleClose} className="pos-cash-form">
          <h4>Cerrar caja</h4>
          <label>
            <span>Conteo final</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={closeForm.amount}
              onChange={(event) =>
                setCloseForm((prev) => ({ ...prev, amount: Number(event.target.value) }))
              }
              required
            />
          </label>
          <label>
            <span>Notas</span>
            <input
              type="text"
              value={closeForm.notes}
              onChange={(event) => setCloseForm((prev) => ({ ...prev, notes: event.target.value }))}
              placeholder="Diferencias u observaciones"
            />
          </label>
          <label>
            <span>Motivo corporativo</span>
            <input
              type="text"
              minLength={5}
              value={closeForm.reason}
              onChange={(event) =>
                setCloseForm((prev) => ({ ...prev, reason: event.target.value }))
              }
              required
            />
          </label>
          <button type="submit" className="btn btn--secondary" disabled={loadingAction === "close"}>
            {loadingAction === "close" ? "Cerrando…" : "Cerrar caja"}
          </button>
        </form>
      </div>
    </section>
  );
}
