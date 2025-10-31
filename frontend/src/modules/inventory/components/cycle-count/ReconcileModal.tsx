import { useState } from "react";
import type { DiscrepancyRow } from "./DiscrepanciesTable";

type Props = {
  open?: boolean;
  diffs?: DiscrepancyRow[];
  onClose?: () => void;
  onSubmit?: (payload: { note: string }) => void;
};

function ReconcileModal({ open, diffs, onClose, onSubmit }: Props) {
  const [note, setNote] = useState<string>("");

  const list = Array.isArray(diffs) ? diffs : [];
  const hasDiffs = list.length > 0;

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <header className="modal-card__header">
          <h3>Conciliar diferencias</h3>
        </header>
        <div className="modal-card__body">
          {!hasDiffs ? (
            <p className="muted">No hay diferencias pendientes.</p>
          ) : (
            <ul className="diff-list">
              {list.map((diff) => (
                <li key={diff.id}>
                  <span>
                    {diff.sku ?? "—"} · {diff.name}
                  </span>
                  <strong>{diff.delta}</strong>
                </li>
              ))}
            </ul>
          )}
          <label>
            <span>Notas de conciliación</span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Detalle los ajustes aplicados"
            />
          </label>
        </div>
        <footer className="modal-card__footer">
          <button type="button" className="ghost" onClick={onClose}>
            Cerrar
          </button>
          <button
            type="button"
            className="primary"
            disabled={!hasDiffs}
            onClick={() => onSubmit?.({ note: note.trim() })}
          >
            Conciliar
          </button>
        </footer>
      </div>
    </div>
  );
}

export default ReconcileModal;
