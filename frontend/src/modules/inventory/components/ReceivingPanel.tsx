import { FormEvent, useCallback, useMemo, useState } from "react";

import POSQuickScan from "../../sales/components/pos/POSQuickScan";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";
import type {
  InventoryReceivingLineInput,
  InventoryReceivingRequest,
  InventoryReceivingResult,
} from "../../../api";
import normalizeIdentifier from "./utils/normalizeIdentifier";

type DraftEntry = InventoryReceivingLineInput & { identifier: string };

type Props = {
  title?: string;
};

function ReceivingPanel({ title = "Recepción rápida" }: Props) {
  const {
    token,
    selectedStoreId,
    pushToast,
    setError,
    refreshInventoryAfterTransfer,
  } = useDashboard();
  const [note, setNote] = useState("Recepción inventario");
  const [responsible, setResponsible] = useState("");
  const [reference, setReference] = useState("");
  const [entries, setEntries] = useState<DraftEntry[]>([]);
  const [manualIdentifier, setManualIdentifier] = useState("");
  const [manualQuantity, setManualQuantity] = useState(1);
  const [manualCost, setManualCost] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InventoryReceivingResult | null>(null);

  const totalQuantity = useMemo(
    () => entries.reduce((sum, entry) => sum + (entry.quantity ?? 0), 0),
    [entries],
  );

  const handleScan = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim();
      if (!trimmed) {
        return "Lectura vacía";
      }
      setEntries((prev) => {
        if (prev.some((item) => item.identifier === trimmed)) {
          return prev;
        }
        const base = normalizeIdentifier(trimmed);
        return [...prev, { ...base, identifier: trimmed, quantity: 1 }];
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
      if (prev.some((item) => item.identifier === trimmed)) {
        return prev;
      }
      const base = normalizeIdentifier(trimmed);
      return [
        ...prev,
        {
          ...base,
          identifier: trimmed,
          quantity: Math.max(1, manualQuantity),
          unit_cost: manualCost ? Number.parseFloat(manualCost) : undefined,
        },
      ];
    });
    setManualIdentifier("");
    setManualQuantity(1);
    setManualCost("");
  }, [manualCost, manualIdentifier, manualQuantity]);

  const handleUpdateQuantity = useCallback((identifier: string, nextValue: number) => {
    setEntries((prev) =>
      prev.map((entry) =>
        entry.identifier === identifier
          ? { ...entry, quantity: Math.max(1, nextValue) }
          : entry,
      ),
    );
  }, []);

  const handleUpdateCost = useCallback((identifier: string, value: string) => {
    setEntries((prev) =>
      prev.map((entry) =>
        entry.identifier === identifier
          ? {
              ...entry,
              unit_cost:
                value.trim().length === 0 || Number.isNaN(Number.parseFloat(value))
                  ? undefined
                  : Number.parseFloat(value),
            }
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
        pushToast({ message: "Selecciona una sucursal para registrar la recepción.", variant: "error" });
        return;
      }
      if (entries.length === 0) {
        pushToast({ message: "Agrega al menos un identificador antes de continuar.", variant: "warning" });
        return;
      }
      const trimmedNote = note.trim();
      if (trimmedNote.length < 5) {
        pushToast({ message: "El motivo debe tener al menos 5 caracteres.", variant: "error" });
        return;
      }
      const request: InventoryReceivingRequest = {
        store_id: selectedStoreId,
        note: trimmedNote,
        responsible: responsible.trim() || undefined,
        reference: reference.trim() || undefined,
        lines: entries.map((entry) => {
          const base = normalizeIdentifier(entry.identifier);
          const normalizedQuantity = Math.max(1, entry.quantity ?? 1);
          return {
            ...base,
            quantity: normalizedQuantity,
            unit_cost: entry.unit_cost,
          } satisfies InventoryReceivingLineInput;
        }),
      };

      try {
        setLoading(true);
        const response = await inventoryService.registerReceiving(token, request, trimmedNote);
        setResult(response);
        setEntries([]);
        pushToast({
          message: `Se registraron ${response.totals.total_quantity} unidades recibidas`,
          variant: "success",
        });
        await refreshInventoryAfterTransfer();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "No fue posible registrar la recepción.";
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
            Escanea IMEIs o agrega identificadores manualmente para registrar entradas.
          </p>
        </div>
      </header>

      <div className="card-section">
        <POSQuickScan onSubmit={handleScan} />
      </div>

      <form onSubmit={handleSubmit} className="form-grid">
        <div className="form-row">
          <label htmlFor="receiving-note">Motivo corporativo</label>
          <textarea
            id="receiving-note"
            required
            minLength={5}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Describe el motivo de la recepción"
          />
        </div>

        <div className="form-row">
          <label htmlFor="receiving-responsible">Responsable</label>
          <input
            id="receiving-responsible"
            value={responsible}
            onChange={(event) => setResponsible(event.target.value)}
            placeholder="Nombre del supervisor"
          />
        </div>

        <div className="form-row">
          <label htmlFor="receiving-reference">Referencia</label>
          <input
            id="receiving-reference"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Folio o documento (opcional)"
          />
        </div>

        <div className="form-row">
          <label htmlFor="receiving-manual">Agregar manualmente</label>
          <div className="scan-bar">
            <input
              id="receiving-manual"
              value={manualIdentifier}
              onChange={(event) => setManualIdentifier(event.target.value)}
              placeholder="IMEI o serial"
            />
            <input
              type="number"
              min={1}
              step={1}
              value={manualQuantity}
              onChange={(event) => {
                const next = Number.parseInt(event.target.value, 10);
                setManualQuantity(Number.isNaN(next) ? 1 : Math.max(1, next));
              }}
              style={{ width: 80 }}
              aria-label="Cantidad"
            />
            <input
              type="number"
              min={0}
              step={0.01}
              value={manualCost}
              onChange={(event) => setManualCost(event.target.value)}
              style={{ width: 120 }}
              placeholder="Costo"
              aria-label="Costo unitario"
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
                <th>Cantidad</th>
                <th>Costo unitario</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted-text">
                    Captura códigos para listarlos aquí.
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
                        min={1}
                        step={1}
                        value={entry.quantity ?? 1}
                        onChange={(event) =>
                          handleUpdateQuantity(
                            entry.identifier,
                            Number.parseInt(event.target.value, 10) || 1,
                          )
                        }
                        aria-label={`Cantidad para ${entry.identifier}`}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={0}
                        step={0.01}
                        value={
                          typeof entry.unit_cost === "number" && Number.isFinite(entry.unit_cost)
                            ? entry.unit_cost
                            : ""
                        }
                        onChange={(event) => handleUpdateCost(entry.identifier, event.target.value)}
                        aria-label={`Costo para ${entry.identifier}`}
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
          <span>Total unidades: {totalQuantity}</span>
        </div>

        <div className="actions-bar actions-bar--end">
          <button type="submit" className="primary" disabled={disableSubmit}>
            {loading ? "Registrando…" : "Registrar recepción"}
          </button>
        </div>
      </form>

      {result ? (
        <section className="card-section" aria-live="polite">
          <h3>Última recepción</h3>
          <p className="muted-text">
            {result.processed.length} elementos registrados · {result.totals.total_quantity} unidades.
          </p>
          <ul className="receipt-list">
            {result.processed.map((item) => (
              <li key={`${item.identifier}-${item.device_id}`}>
                <strong>{item.identifier}</strong> — movimiento #{item.movement.id} en {item.movement.sucursal_destino ?? "sucursal"}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

export default ReceivingPanel;
