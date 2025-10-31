import { useMemo, useState } from "react";
import ReasonSelector from "./ReasonSelector";

export type AdjustmentLineDraft = {
  id: string;
  sku?: string;
  name?: string;
  qty: number;
  imeis?: string[];
};

type Props = {
  open?: boolean;
  onClose?: () => void;
  onSubmit?: (payload: { warehouse: string; reason: string; note: string; lines: AdjustmentLineDraft[] }) => void;
};

const createId = () => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const createEmptyLine = (): AdjustmentLineDraft => ({
  id: createId(),
  sku: "",
  name: "",
  qty: 0,
  imeis: [],
});

function CreateAdjustmentModal({ open, onClose, onSubmit }: Props) {
  const [warehouse, setWarehouse] = useState<string>("");
  const [reason, setReason] = useState<string>("CORRECTION");
  const [note, setNote] = useState<string>("");
  const [lines, setLines] = useState<AdjustmentLineDraft[]>([createEmptyLine()]);

  const imeiState = useMemo(() => {
    const seen = new Set<string>();
    const duplicated = new Set<string>();
    lines.forEach((line) => {
      (line.imeis ?? []).forEach((imei) => {
        const normalized = imei.trim();
        if (!normalized) {
          return;
        }
        if (seen.has(normalized)) {
          duplicated.add(normalized);
        }
        seen.add(normalized);
      });
    });
    return { duplicated };
  }, [lines]);

  const invalidLines = lines.filter((line) => !line.name?.trim() || line.qty <= 0);
  const hasDuplicates = imeiState.duplicated.size > 0;
  const canSubmit = Boolean(
    open &&
      warehouse.trim() &&
      lines.length > 0 &&
      invalidLines.length === 0 &&
      !hasDuplicates
  );

  const handleLineChange = (id: string, patch: Partial<AdjustmentLineDraft>) => {
    setLines((state) => state.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const handleLineImeisChange = (id: string, value: string) => {
    const tokens = value
      .split(",")
      .map((token) => token.trim())
      .filter(Boolean);
    const unique = Array.from(new Set(tokens));
    handleLineChange(id, { imeis: unique });
  };

  const handleAddLine = () => {
    setLines((state) => [...state, createEmptyLine()]);
  };

  const handleRemoveLine = (id: string) => {
    setLines((state) => (state.length > 1 ? state.filter((line) => line.id !== id) : state));
  };

  const handleSubmit = () => {
    if (!canSubmit) {
      return;
    }
    onSubmit?.({
      warehouse: warehouse.trim(),
      reason,
      note: note.trim(),
      lines,
    });
  };

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <header className="modal-card__header">
          <h3>Nuevo ajuste de inventario</h3>
        </header>
        <div className="modal-card__body">
          <label>
            <span>Almacén / Sucursal</span>
            <input value={warehouse} onChange={(event) => setWarehouse(event.target.value)} placeholder="Ej. Sucursal Centro" />
          </label>
          <label>
            <span>Notas</span>
            <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Motivo interno o comentarios" />
          </label>
          <div>
            <span className="field-label">Motivo</span>
            <ReasonSelector value={reason} onChange={setReason} />
          </div>
          <div className="lines-table">
            {lines.map((line) => (
              <div key={line.id} className="lines-table__row">
                <input
                  placeholder="SKU"
                  value={line.sku ?? ""}
                  onChange={(event) => handleLineChange(line.id, { sku: event.target.value })}
                />
                <input
                  placeholder="Producto"
                  value={line.name ?? ""}
                  onChange={(event) => handleLineChange(line.id, { name: event.target.value })}
                />
                <input
                  type="number"
                  min={0}
                  placeholder="Cantidad"
                  value={line.qty}
                  onChange={(event) => handleLineChange(line.id, { qty: Number(event.target.value || 0) })}
                />
                <input
                  placeholder="IMEIs (separados por coma)"
                  value={(line.imeis ?? []).join(",")}
                  onChange={(event) => handleLineImeisChange(line.id, event.target.value)}
                />
                <button type="button" className="ghost" onClick={() => handleRemoveLine(line.id)}>
                  Quitar
                </button>
              </div>
            ))}
            <button type="button" className="ghost" onClick={handleAddLine}>
              Agregar línea
            </button>
          </div>
          {invalidLines.length > 0 ? (
            <p className="form-error">Verifica que todas las líneas tengan producto y cantidad positiva.</p>
          ) : null}
          {hasDuplicates ? (
            <p className="form-error">Los IMEIs/seriales deben ser únicos en el ajuste.</p>
          ) : null}
        </div>
        <footer className="modal-card__footer">
          <button type="button" className="ghost" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="primary" disabled={!canSubmit} onClick={handleSubmit}>
            Crear ajuste
          </button>
        </footer>
      </div>
    </div>
  );
}

export default CreateAdjustmentModal;
