import { useState } from "react";
import type { CyclePlan } from "./PlanBar";

type Props = {
  open?: boolean;
  plan: CyclePlan;
  onClose?: () => void;
  onSubmit?: (payload: { plan: CyclePlan; responsible: string; note: string }) => void;
};

function StartCountModal({ open, plan, onClose, onSubmit }: Props) {
  const [responsible, setResponsible] = useState<string>("");
  const [note, setNote] = useState<string>("");

  const valid = Boolean(open && responsible.trim());

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <header className="modal-card__header">
          <h3>Iniciar conteo cíclico</h3>
        </header>
        <div className="modal-card__body">
          <div className="modal-summary">
            <h4>Resumen de plan</h4>
            <ul>
              <li>Almacén: {plan.warehouse ?? "—"}</li>
              <li>Área: {plan.area ?? "—"}</li>
              <li>Familias: {plan.families ?? "—"}</li>
              <li>Frecuencia: {plan.frequency ?? "WEEKLY"}</li>
            </ul>
          </div>
          <label>
            <span>Responsable</span>
            <input
              value={responsible}
              onChange={(event) => setResponsible(event.target.value)}
              placeholder="Nombre de supervisor"
            />
          </label>
          <label>
            <span>Notas iniciales</span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Instrucciones o consideraciones"
            />
          </label>
        </div>
        <footer className="modal-card__footer">
          <button type="button" className="ghost" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="primary"
            disabled={!valid}
            onClick={() => onSubmit?.({ plan, responsible: responsible.trim(), note: note.trim() })}
          >
            Iniciar conteo
          </button>
        </footer>
      </div>
    </div>
  );
}

export default StartCountModal;
