import { useState } from "react";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { boxes: number; weight: number; volume: string }) => void;
};

function PackModal({ open, onClose, onSubmit }: Props) {
  const [boxes, setBoxes] = useState<number>(1);
  const [weight, setWeight] = useState<number>(0);
  const [volume, setVolume] = useState<string>("");

  const valid = boxes > 0 && weight >= 0;

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <header className="modal-card__header">
          <h3>Empaquetado</h3>
        </header>
        <div className="modal-card__body">
          <label>
            <span>Cajas</span>
            <input
              type="number"
              min={1}
              value={boxes}
              onChange={(event) => setBoxes(Math.max(0, Number(event.target.value || 0)))}
            />
          </label>
          <label>
            <span>Peso (kg)</span>
            <input
              type="number"
              min={0}
              value={weight}
              onChange={(event) => setWeight(Math.max(0, Number(event.target.value || 0)))}
            />
          </label>
          <label>
            <span>Volumen</span>
            <input value={volume} onChange={(event) => setVolume(event.target.value)} placeholder="Ej. 0.25 m³" />
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
            onClick={() => onSubmit?.({ boxes, weight, volume: volume.trim() })}
          >
            Confirmar empaquetado
          </button>
        </footer>
      </div>
    </div>
  );
}

export default PackModal;
