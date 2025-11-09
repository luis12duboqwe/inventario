import { FormEvent, useCallback, useMemo, useState } from "react";

import POSQuickScan from "../../sales/components/pos/POSQuickScan";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";
import type {
  InventoryCycleCountRequest,
  InventoryCycleCountResult,
  InventoryCountLineInput,
} from "../../../api";

import normalizeIdentifier from "./utils/normalizeIdentifier";

type DraftEntry = InventoryCountLineInput & { identifier: string };

type Props = {
  title?: string;
};

function CountingPanel({ title = "Conteo cíclico" }: Props) {
  const { token, selectedStoreId, pushToast, setError, refreshInventoryAfterTransfer } = useDashboard();
  const [note, setNote] = useState("Conteo cíclico inventario");
  const [responsible, setResponsible] = useState("");
  const [reference, setReference] = useState("");
  const [entries, setEntries] = useState<DraftEntry[]>([]);
  const [manualIdentifier, setManualIdentifier] = useState("");
  const [manualCount, setManualCount] = useState(1);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InventoryCycleCountResult | null>(null);

  const totalCounted = useMemo(
    () => entries.reduce((sum, entry) => sum + (entry.counted ?? 0), 0),
    [entries],
  );

  const handleScan = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim();
      if (!trimmed) {
        return "Lectura vacía";
      }
      setEntries((prev) => {
        const existing = prev.find((entry) => entry.identifier === trimmed);
        if (existing) {
          return prev.map((entry) =>
            entry.identifier === trimmed
              ? { ...entry, counted: (entry.counted ?? 0) + 1 }
              : entry,
          );
        }
        const base = normalizeIdentifier(trimmed);
        return [...prev, { ...base, identifier: trimmed, counted: 1 }];
      });
      return { label: trimmed };
    },
    [],
  );

  const handleAddManual = useCallback(() => {
    const trimmed = manualIdentifier.trim();
    if (!trimmed) {
      return;
    }
    setEntries((prev) => {
      const base = normalizeIdentifier(trimmed);
      if (prev.some((entry) => entry.identifier === trimmed)) {
        return prev.map((entry) =>
          entry.identifier === trimmed
            ? { ...entry, counted: Math.max(0, manualCount) }
            : entry,
        );
      }
      return [...prev, { ...base, identifier: trimmed, counted: Math.max(0, manualCount) }];
    });
    setManualIdentifier("");
    setManualCount(1);
  }, [manualCount, manualIdentifier]);

  const handleUpdateCount = useCallback((identifier: string, value: number) => {
    setEntries((prev) =>
      prev.map((entry) =>
        entry.identifier === identifier
          ? { ...entry, counted: Math.max(0, value) }
          : entry,
      ),
    );
  }, []);

  const handleRemove = useCallback((identifier: string) => {
    setEntries((prev) => prev.filter((entry) => entry.identifier !== identifier));
  }, []);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedStoreId) {
        pushToast({ message: "Selecciona una sucursal para conciliar el conteo.", variant: "error" });
        return;
      }
      if (entries.length === 0) {
        pushToast({ message: "Agrega identificadores antes de conciliar.", variant: "warning" });
        return;
      }
      const trimmedNote = note.trim();
      if (trimmedNote.length < 5) {
        pushToast({ message: "El motivo debe tener al menos 5 caracteres.", variant: "error" });
        return;
      }
      const request: InventoryCycleCountRequest = {
        store_id: selectedStoreId,
        note: trimmedNote,
        responsible: responsible.trim() || undefined,
        reference: reference.trim() || undefined,
        lines: entries.map((entry) => ({
          ...normalizeIdentifier(entry.identifier),
          counted: Math.max(0, entry.counted ?? 0),
        })),
      };
      try {
        setLoading(true);
        const response = await inventoryService.registerCycleCount(token, request, trimmedNote);
        setResult(response);
        setEntries([]);
        pushToast({
          message: `Conteo registrado. Ajustes generados: ${response.totals.adjusted}.`,
          variant: "success",
        });
        await refreshInventoryAfterTransfer();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible conciliar el conteo.";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        setLoading(false);
      }
    },
    [
      entries,
      note,
      pushToast,
      refreshInventoryAfterTransfer,
      reference,
      responsible,
      selectedStoreId,
      setError,
      token,
    ],
  );

  const disableSubmit =
    loading || !selectedStoreId || entries.length === 0 || note.trim().length < 5;

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>{title}</h2>
          <p className="card-subtitle">
            Escanea equipos para comparar contra el inventario y generar ajustes automáticamente.
          </p>
        </div>
      </header>

      <div className="card-section">
        <POSQuickScan onSubmit={handleScan} />
      </div>

      <form onSubmit={handleSubmit} className="form-grid">
        <div className="form-row">
          <label htmlFor="counting-note">Motivo corporativo</label>
          <textarea
            id="counting-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            required
            minLength={5}
            placeholder="Describe el motivo del conteo"
          />
        </div>

        <div className="form-row">
          <label htmlFor="counting-responsible">Responsable</label>
          <input
            id="counting-responsible"
            value={responsible}
            onChange={(event) => setResponsible(event.target.value)}
            placeholder="Nombre del auditor"
          />
        </div>

        <div className="form-row">
          <label htmlFor="counting-reference">Referencia</label>
          <input
            id="counting-reference"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Folio o documento (opcional)"
          />
        </div>

        <div className="form-row">
          <label htmlFor="counting-manual">Agregar manualmente</label>
          <div className="scan-bar">
            <input
              id="counting-manual"
              value={manualIdentifier}
              onChange={(event) => setManualIdentifier(event.target.value)}
              placeholder="IMEI o serial"
            />
            <input
              type="number"
              min={0}
              step={1}
              value={manualCount}
              onChange={(event) => {
                const next = Number.parseInt(event.target.value, 10);
                setManualCount(Number.isNaN(next) ? 0 : Math.max(0, next));
              }}
              style={{ width: 80 }}
              aria-label="Conteo"
            />
            <button type="button" className="ghost" onClick={handleAddManual}>
              Agregar
            </button>
          </div>
        </div>

        <div className="table-wrapper" role="region" aria-live="polite">
          <table>
            <thead>
              <tr>
                <th>Identificador</th>
                <th>Contados</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={3} className="muted-text">
                    Escanea códigos para iniciar el conteo.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.identifier}>
                    <td>
                      <strong>{entry.identifier}</strong>
                    </td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        step={1}
                        value={entry.counted ?? 0}
                        onChange={(event) =>
                          handleUpdateCount(
                            entry.identifier,
                            Number.parseInt(event.target.value, 10) || 0,
                          )
                        }
                        aria-label={`Conteo para ${entry.identifier}`}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ghost"
                        onClick={() => handleRemove(entry.identifier)}
                      >
                        Quitar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="summary-row">
          <span>Total contados: {totalCounted}</span>
        </div>

        <div className="actions-bar actions-bar--end">
          <button type="submit" className="primary" disabled={disableSubmit}>
            {loading ? "Conciliando…" : "Conciliar diferencias"}
          </button>
        </div>
      </form>

      {result ? (
        <section className="card-section" aria-live="polite">
          <h3>Resultados</h3>
          <p className="muted-text">
            {result.totals.adjusted} ajustes · {result.totals.matched} coincidencias · Variación total {result.totals.total_variance} unidades.
          </p>
          {result.adjustments.length === 0 ? (
            <p className="muted-text">Sin discrepancias pendientes.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Dispositivo</th>
                    <th>Esperado</th>
                    <th>Contado</th>
                    <th>Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {result.adjustments.map((adjustment) => (
                    <tr key={`${adjustment.identifier ?? adjustment.device_id}`}>
                      <td>{adjustment.identifier ?? adjustment.sku ?? `ID ${adjustment.device_id}`}</td>
                      <td>{adjustment.expected}</td>
                      <td>{adjustment.counted}</td>
                      <td>{adjustment.delta}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}
    </section>
  );
}

export default CountingPanel;
