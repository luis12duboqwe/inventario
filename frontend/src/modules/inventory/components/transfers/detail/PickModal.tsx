import { useMemo, useState } from "react";

export type PickLine = {
  id: string;
  name: string;
  qty: number;
  picked?: number;
};

type Props = {
  open?: boolean;
  lines?: PickLine[];
  onClose?: () => void;
  onSubmit?: (payload: { qtys: Record<string, number> }) => void;
};

function PickModal({ open, lines, onClose, onSubmit }: Props) {
  const [qtys, setQtys] = useState<Record<string, number>>({});

  const entries = useMemo(() => (Array.isArray(lines) ? lines : []), [lines]);

  const limits = useMemo(() => {
    return entries.reduce<Record<string, number>>((acc, line) => {
      const already = line.picked ?? 0;
      acc[line.id] = Math.max(0, line.qty - already);
      return acc;
    }, {});
  }, [entries]);

  const invalid = entries.some((line) => {
    const limit = limits[line.id] ?? 0;
    const value = qtys[line.id] ?? 0;
    return value < 0 || value > limit || value === 0;
  });

  const hasLines = entries.length > 0;
  const canSubmit = open && hasLines && !invalid;

  if (!open) {
    return null;
  }

  const handleChange = (id: string, raw: number) => {
    const safe = Number.isFinite(raw) ? Math.max(0, raw) : 0;
    setQtys((state) => ({ ...state, [id]: safe }));
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <header className="modal-card__header">
          <h3>Confirmar picking</h3>
        </header>
        <div className="modal-card__body">
          {entries.map((line) => {
            const max = limits[line.id] ?? 0;
            const value = qtys[line.id] ?? 0;
            return (
              <div key={line.id} className="modal-row">
                <div>
                  <strong>{line.name}</strong>
                  <p className="muted">Solicitado {line.qty} · Pendiente {max}</p>
                </div>
                <input
                  type="number"
                  min={0}
                  max={max}
                  value={value}
                  onChange={(event) => handleChange(line.id, Number(event.target.value || 0))}
                />
              </div>
            );
          })}
          {!hasLines ? <p className="muted">Sin líneas para picking.</p> : null}
          {invalid && hasLines ? (
            <p className="form-error">Ingresa cantidades positivas sin exceder lo solicitado.</p>
          ) : null}
        </div>
        <footer className="modal-card__footer">
          <button type="button" className="ghost" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="primary" disabled={!canSubmit} onClick={() => onSubmit?.({ qtys })}>
            Confirmar picking
          </button>
        </footer>
      </div>
    </div>
  );
}

export default PickModal;
