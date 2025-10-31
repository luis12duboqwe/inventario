import { useMemo, useState } from "react";

export type ReceiveLine = {
  id: string;
  name: string;
  qty: number;
  shipped?: number;
  allowSerial?: boolean;
};

type Props = {
  open?: boolean;
  lines?: ReceiveLine[];
  onClose?: () => void;
  onSubmit?: (payload: { qtys: Record<string, number>; serials: Record<string, string[]> }) => void;
};

function ReceiveModal({ open, lines, onClose, onSubmit }: Props) {
  const [qtys, setQtys] = useState<Record<string, number>>({});
  const [serials, setSerials] = useState<Record<string, string[]>>({});

  const entries = useMemo(() => (Array.isArray(lines) ? lines : []), [lines]);

  const limits = useMemo(() => {
    return entries.reduce<Record<string, number>>((acc, line) => {
      const shipped = line.shipped ?? line.qty;
      acc[line.id] = Math.max(0, Math.min(line.qty, shipped));
      return acc;
    }, {});
  }, [entries]);

  const serialDuplicates = useMemo(() => {
    const seen = new Set<string>();
    const duplicates = new Set<string>();
    Object.values(serials).forEach((list) => {
      list.forEach((serial) => {
        const normalized = serial.trim();
        if (!normalized) {
          return;
        }
        if (seen.has(normalized)) {
          duplicates.add(normalized);
        }
        seen.add(normalized);
      });
    });
    return duplicates;
  }, [serials]);

  const invalidLine = entries.some((line) => {
    const value = qtys[line.id] ?? 0;
    const limit = limits[line.id];
    if (value < 0 || value > limit) {
      return true;
    }
    if (line.allowSerial) {
      const current = serials[line.id] ?? [];
      if (value > 0 && current.length !== value) {
        return true;
      }
    }
    return false;
  });

  const hasQty = entries.some((line) => (qtys[line.id] ?? 0) > 0);
  const canSubmit = Boolean(open && !invalidLine && serialDuplicates.size === 0 && hasQty);

  if (!open) {
    return null;
  }

  const handleQtyChange = (id: string, raw: number) => {
    const safe = Number.isFinite(raw) ? Math.max(0, raw) : 0;
    setQtys((state) => ({ ...state, [id]: safe }));
  };

  const handleSerialsChange = (id: string, value: string) => {
    const tokens = value
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);
    const unique = Array.from(new Set(tokens));
    setSerials((state) => ({ ...state, [id]: unique }));
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card modal-card--lg">
        <header className="modal-card__header">
          <h3>Recepción</h3>
        </header>
        <div className="modal-card__body">
          {entries.map((line) => {
            const limit = limits[line.id];
            const value = qtys[line.id] ?? 0;
            return (
              <div key={line.id} className="modal-panel">
                <div className="modal-panel__header">
                  <div>
                    <strong>{line.name}</strong>
                    <p className="muted">Solicitado {line.qty} · Enviado {line.shipped ?? line.qty}</p>
                  </div>
                  <input
                    type="number"
                    min={0}
                    max={limit}
                    value={value}
                    onChange={(event) => handleQtyChange(line.id, Number(event.target.value || 0))}
                  />
                </div>
                {line.allowSerial ? (
                  <textarea
                    value={(serials[line.id] ?? []).join(",")}
                    onChange={(event) => handleSerialsChange(line.id, event.target.value)}
                    placeholder="IMEIs/seriales separados por coma"
                  />
                ) : (
                  <p className="muted">No se requieren seriales</p>
                )}
              </div>
            );
          })}
          {entries.length === 0 ? <p className="muted">Sin líneas para recibir.</p> : null}
          {invalidLine ? <p className="form-error">Verifica cantidades y seriales por línea.</p> : null}
          {serialDuplicates.size > 0 ? (
            <p className="form-error">Los seriales deben ser únicos en la recepción.</p>
          ) : null}
        </div>
        <footer className="modal-card__footer">
          <button type="button" className="ghost" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="primary"
            disabled={!canSubmit}
            onClick={() => onSubmit?.({ qtys, serials })}
          >
            Confirmar recepción
          </button>
        </footer>
      </div>
    </div>
  );
}

export default ReceiveModal;
