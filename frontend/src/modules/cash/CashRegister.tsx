import { FormEvent, useMemo, useState } from "react";

import type { CashRegisterEntry } from "../../api";

type CashRegisterProps = {
  session: { id: number } | null;
  entries: CashRegisterEntry[];
  loading: boolean;
  error: string | null;
  denominations: Record<string, number>;
  onDenominationChange: (value: number, quantity: number) => void;
  reconciliationNotes: string;
  onReconciliationNotesChange: (value: string) => void;
  differenceReason: string;
  onDifferenceReasonChange: (value: string) => void;
  onRegisterEntry: (payload: {
    type: CashRegisterEntry["entry_type"];
    amount: number;
    reason: string;
    notes?: string;
  }) => Promise<void>;
  onRefreshEntries: () => Promise<void>;
  onDownloadReport: () => Promise<void>;
};

const DENOMINATIONS: number[] = [
  1000,
  500,
  200,
  100,
  50,
  20,
  10,
  5,
  2,
  1,
  0.5,
  0.2,
  0.1,
];

function CashRegister({
  session,
  entries,
  loading,
  error,
  denominations,
  onDenominationChange,
  reconciliationNotes,
  onReconciliationNotesChange,
  differenceReason,
  onDifferenceReasonChange,
  onRegisterEntry,
  onRefreshEntries,
  onDownloadReport,
}: CashRegisterProps) {
  const [entryType, setEntryType] = useState<CashRegisterEntry["entry_type"]>("INGRESO");
  const [entryAmount, setEntryAmount] = useState<number>(0);
  const [entryReason, setEntryReason] = useState("");
  const [entryNotes, setEntryNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const denominationRows = useMemo(
    () =>
      DENOMINATIONS.map((value) => ({
        value,
        quantity: denominations[value.toFixed(2)] ?? 0,
      })),
    [denominations],
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!session || submitting) {
      return;
    }
    setSubmitting(true);
    try {
      await onRegisterEntry({
        type: entryType,
        amount: entryAmount,
        reason: entryReason,
        notes: entryNotes,
      });
      setEntryAmount(0);
      setEntryReason("");
      setEntryNotes("");
    } catch {
      // El controlador se encargará de exponer el error.
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="card">
      <header className="card__header">
        <div>
          <h3 className="card__title">Movimientos manuales de caja</h3>
          <p className="card__subtitle">
            Registra ingresos y egresos vinculados a la sesión activa y documenta conciliaciones con motivo.
          </p>
        </div>
        <div className="actions-row">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              void onRefreshEntries();
            }}
            disabled={loading || !session}
          >
            {loading ? "Actualizando…" : "Actualizar movimientos"}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              void onDownloadReport();
            }}
            disabled={!session}
          >
            Descargar cierre (PDF)
          </button>
        </div>
      </header>

      {error ? <p className="alert error">{error}</p> : null}
      {!session ? (
        <p className="muted-text">Abre una sesión de caja para registrar ingresos o egresos manuales.</p>
      ) : (
        <div className="cash-register-grid">
          <form className="form-grid" onSubmit={handleSubmit}>
            <h4 className="form-span">Registrar movimiento</h4>
            <label>
              <span>Tipo</span>
              <select value={entryType} onChange={(event) => setEntryType(event.target.value as CashRegisterEntry["entry_type"])}>
                <option value="INGRESO">Ingreso</option>
                <option value="EGRESO">Egreso</option>
              </select>
            </label>
            <label>
              <span>Monto</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={entryAmount}
                onChange={(event) => setEntryAmount(Number(event.target.value))}
                required
              />
            </label>
            <label className="form-span">
              <span>Motivo corporativo</span>
              <input
                type="text"
                minLength={5}
                value={entryReason}
                onChange={(event) => setEntryReason(event.target.value)}
                required
                placeholder="Describe la razón del movimiento"
              />
            </label>
            <label className="form-span">
              <span>Notas internas</span>
              <input
                type="text"
                value={entryNotes}
                onChange={(event) => setEntryNotes(event.target.value)}
                placeholder="Observaciones adicionales (opcional)"
              />
            </label>
            <div className="form-actions form-span">
              <button type="submit" className="btn btn--primary" disabled={submitting}>
                {submitting ? "Guardando…" : "Registrar movimiento"}
              </button>
            </div>
          </form>

          <div className="cash-register-side">
            <h4>Conciliación y diferencias</h4>
            <label>
              <span>Notas de conciliación</span>
              <textarea
                value={reconciliationNotes}
                onChange={(event) => onReconciliationNotesChange(event.target.value)}
                placeholder="Describe el proceso de conciliación o responsables"
                rows={3}
              />
            </label>
            <label>
              <span>Motivo de diferencia</span>
              <textarea
                value={differenceReason}
                onChange={(event) => onDifferenceReasonChange(event.target.value)}
                placeholder="Requerido cuando exista diferencia contra lo esperado"
                rows={3}
              />
            </label>
            <h4>Denominaciones en caja</h4>
            <div className="denomination-grid">
              {denominationRows.map(({ value, quantity }) => (
                <label key={value}>
                  <span>{value >= 1 ? `$${value.toFixed(0)}` : `$${value.toFixed(2)}`}</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={quantity}
                    onChange={(event) => onDenominationChange(value, Number(event.target.value))}
                  />
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {entries.length > 0 ? (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Monto</th>
                <th>Motivo</th>
                <th>Registrado</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.entry_type === "INGRESO" ? "Ingreso" : "Egreso"}</td>
                  <td>${entry.amount.toFixed(2)}</td>
                  <td>{entry.reason}</td>
                  <td>{new Date(entry.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted-text">No hay movimientos manuales registrados en esta sesión.</p>
      )}
    </section>
  );
}

export default CashRegister;
