import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import POSQuickScan from "../../sales/components/pos/POSQuickScan";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { inventoryService } from "../services/inventoryService";
import type {
  InventoryReceivingDistributionInput,
  InventoryReceivingLineInput,
  InventoryReceivingRequest,
  InventoryReceivingResult,
} from "@api/inventory";
import type { TransferOrder } from "@api/transfers";
import normalizeIdentifier from "./utils/normalizeIdentifier";

type DraftEntry = InventoryReceivingLineInput & {
  identifier: string;
  distributions: InventoryReceivingDistributionInput[];
};

type DistributionDraft = {
  storeId: number | "";
  quantity: number;
};

type Props = {
  title?: string;
};

function ReceivingPanel({ title = "Recepción rápida" }: Props) {
  const { token, selectedStoreId, pushToast, setError, refreshInventoryAfterTransfer, stores } =
    useDashboard();
  const [note, setNote] = useState("Recepción inventario");
  const [responsible, setResponsible] = useState("");
  const [reference, setReference] = useState("");
  const [entries, setEntries] = useState<DraftEntry[]>([]);
  const [manualIdentifier, setManualIdentifier] = useState("");
  const [manualQuantity, setManualQuantity] = useState(1);
  const [manualCost, setManualCost] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InventoryReceivingResult | null>(null);
  const [distributionDrafts, setDistributionDrafts] = useState<Record<string, DistributionDraft>>(
    {},
  );

  const totalQuantity = useMemo(
    () => entries.reduce((sum, entry) => sum + (entry.quantity ?? 0), 0),
    [entries],
  );

  const storeLookup = useMemo(() => {
    const map = new Map<number, string>();
    stores.forEach((store) => map.set(store.id, store.name));
    return map;
  }, [stores]);

  const destinationStores = useMemo(
    () => stores.filter((store) => store.id !== selectedStoreId),
    [stores, selectedStoreId],
  );

  useEffect(() => {
    if (!selectedStoreId) {
      return;
    }
    setEntries((prev) =>
      prev.map((entry) => ({
        ...entry,
        distributions: (entry.distributions ?? []).filter(
          (allocation) => allocation.store_id !== selectedStoreId,
        ),
      })),
    );
    setDistributionDrafts((current) => {
      const next: Record<string, DistributionDraft> = { ...current };
      Object.entries(next).forEach(([key, draft]) => {
        if (draft.storeId === selectedStoreId) {
          next[key] = { storeId: "", quantity: draft.quantity };
        }
      });
      return next;
    });
  }, [selectedStoreId]);

  const handleScan = useCallback(async (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) {
      return "Lectura vacía";
    }
    let added = false;
    setEntries((prev) => {
      if (prev.some((item) => item.identifier === trimmed)) {
        return prev;
      }
      const base = normalizeIdentifier(trimmed);
      added = true;
      return [...prev, { ...base, identifier: trimmed, quantity: 1, distributions: [] }];
    });
    if (added) {
      setDistributionDrafts((current) => ({
        ...current,
        [trimmed]: current[trimmed] ?? { storeId: "", quantity: 1 },
      }));
    }
    return { label: trimmed };
  }, []);

  const handleAddManual = useCallback(() => {
    const trimmed = manualIdentifier.trim();
    if (!trimmed) {
      return;
    }
    let added = false;
    setEntries((prev) => {
      if (prev.some((item) => item.identifier === trimmed)) {
        return prev;
      }
      const base = normalizeIdentifier(trimmed);
      added = true;
      return [
        ...prev,
        {
          ...base,
          identifier: trimmed,
          quantity: Math.max(1, manualQuantity),
          ...(manualCost ? { unit_cost: Number.parseFloat(manualCost) } : {}),
          distributions: [],
        },
      ];
    });
    if (added) {
      setDistributionDrafts((current) => ({
        ...current,
        [trimmed]: current[trimmed] ?? { storeId: "", quantity: 1 },
      }));
    }
    setManualIdentifier("");
    setManualQuantity(1);
    setManualCost("");
  }, [manualCost, manualIdentifier, manualQuantity]);

  const handleUpdateQuantity = useCallback(
    (identifier: string, nextValue: number) => {
      let showWarning = false;
      setEntries((prev) =>
        prev.map((entry) => {
          if (entry.identifier !== identifier) {
            return entry;
          }
          const nextQuantity = Math.max(1, nextValue);
          const assigned = (entry.distributions ?? []).reduce(
            (sum, allocation) => sum + allocation.quantity,
            0,
          );
          if (assigned > nextQuantity) {
            showWarning = true;
            return entry;
          }
          return { ...entry, quantity: nextQuantity };
        }),
      );
      if (showWarning) {
        pushToast({
          message: "La cantidad asignada a sucursales excede el total disponible.",
          variant: "warning",
        });
      }
    },
    [pushToast],
  );

  const handleUpdateCost = useCallback((identifier: string, value: string) => {
    setEntries((prev) =>
      prev.map((entry) => {
        if (entry.identifier !== identifier) {
          return entry;
        }
        const cost =
          value.trim().length === 0 || Number.isNaN(Number.parseFloat(value))
            ? undefined
            : Number.parseFloat(value);
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { unit_cost, ...rest } = entry;
        return {
          ...rest,
          ...(cost !== undefined ? { unit_cost: cost } : {}),
        };
      }),
    );
  }, []);

  const handleRemove = useCallback((identifier: string) => {
    setEntries((prev) => prev.filter((entry) => entry.identifier !== identifier));
    setDistributionDrafts((current) => {
      if (!(identifier in current)) {
        return current;
      }
      const next = { ...current };
      delete next[identifier];
      return next;
    });
  }, []);

  const handleDistributionDraftChange = useCallback(
    (identifier: string, field: keyof DistributionDraft, value: number | "") => {
      setDistributionDrafts((current) => {
        const draft = current[identifier] ?? { storeId: "", quantity: 1 };
        if (field === "storeId") {
          return {
            ...current,
            [identifier]: { storeId: value as number | "", quantity: draft.quantity },
          };
        }
        const quantityValue = typeof value === "number" && Number.isFinite(value) ? value : 1;
        return {
          ...current,
          [identifier]: { storeId: draft.storeId, quantity: Math.max(1, quantityValue) },
        };
      });
    },
    [],
  );

  const handleAddDistribution = useCallback(
    (identifier: string) => {
      const draft = distributionDrafts[identifier] ?? { storeId: "", quantity: 1 };
      const storeId = draft.storeId;
      const quantity = Math.max(1, draft.quantity);
      if (storeId === "") {
        pushToast({
          message: "Selecciona una sucursal destino para distribuir.",
          variant: "warning",
        });
        return;
      }
      if (selectedStoreId && storeId === selectedStoreId) {
        pushToast({
          message: "Selecciona una sucursal distinta a la de recepción.",
          variant: "warning",
        });
        return;
      }
      let errorMessage: string | null = null;
      let updated = false;
      setEntries((prev) =>
        prev.map((entry) => {
          if (entry.identifier !== identifier) {
            return entry;
          }
          const existing = entry.distributions ?? [];
          if (existing.some((allocation) => allocation.store_id === storeId)) {
            errorMessage = "Ya asignaste esta sucursal para el identificador.";
            return entry;
          }
          const assigned = existing.reduce((sum, allocation) => sum + allocation.quantity, 0);
          const available = Math.max(0, (entry.quantity ?? 1) - assigned);
          if (quantity > available) {
            errorMessage = "La cantidad asignada supera lo disponible para transferir.";
            return entry;
          }
          updated = true;
          return {
            ...entry,
            distributions: [...existing, { store_id: storeId, quantity }],
          };
        }),
      );
      if (errorMessage) {
        pushToast({ message: errorMessage, variant: "warning" });
        return;
      }
      if (updated) {
        setDistributionDrafts((current) => ({
          ...current,
          [identifier]: { storeId: "", quantity: 1 },
        }));
        pushToast({
          message: "Distribución registrada para la transferencia automática.",
          variant: "success",
        });
      }
    },
    [distributionDrafts, pushToast, selectedStoreId],
  );

  const handleRemoveDistribution = useCallback((identifier: string, storeId: number) => {
    setEntries((prev) =>
      prev.map((entry) =>
        entry.identifier === identifier
          ? {
              ...entry,
              distributions: (entry.distributions ?? []).filter(
                (allocation) => allocation.store_id !== storeId,
              ),
            }
          : entry,
      ),
    );
  }, []);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedStoreId) {
        pushToast({
          message: "Selecciona una sucursal para registrar la recepción.",
          variant: "error",
        });
        return;
      }
      if (entries.length === 0) {
        pushToast({
          message: "Agrega al menos un identificador antes de continuar.",
          variant: "warning",
        });
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
        ...(responsible.trim() ? { responsible: responsible.trim() } : {}),
        ...(reference.trim() ? { reference: reference.trim() } : {}),
        lines: entries.map((entry) => {
          const base = normalizeIdentifier(entry.identifier);
          const normalizedQuantity = Math.max(1, entry.quantity ?? 1);
          const distributions =
            entry.distributions && entry.distributions.length > 0 ? entry.distributions : undefined;
          return {
            ...base,
            quantity: normalizedQuantity,
            ...(entry.unit_cost !== undefined ? { unit_cost: entry.unit_cost } : {}),
            ...(distributions ? { distributions } : {}),
          } satisfies InventoryReceivingLineInput;
        }),
      };

      try {
        setLoading(true);
        const response = await inventoryService.registerReceiving(token, request, trimmedNote);
        setResult(response);
        setEntries([]);
        setDistributionDrafts({});
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
                <th>Distribución</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="muted-text">
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
                      <div className="distribution-editor">
                        <div className="distribution-summary">
                          {entry.distributions.length ? (
                            <ul className="inline-list">
                              {entry.distributions.map((allocation) => (
                                <li key={`${entry.identifier}-${allocation.store_id}`}>
                                  <span className="tag">
                                    {storeLookup.get(allocation.store_id) ??
                                      `Sucursal #${allocation.store_id}`}{" "}
                                    · {allocation.quantity}
                                  </span>
                                  <button
                                    type="button"
                                    className="ghost"
                                    onClick={() =>
                                      handleRemoveDistribution(
                                        entry.identifier,
                                        allocation.store_id,
                                      )
                                    }
                                    aria-label={`Quitar distribución a ${
                                      storeLookup.get(allocation.store_id) ?? allocation.store_id
                                    }`}
                                  >
                                    Quitar
                                  </button>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="muted-text">Sin transferencias automáticas</p>
                          )}
                        </div>
                        {destinationStores.length ? (
                          <div className="distribution-form">
                            <select
                              value={(() => {
                                const draft = distributionDrafts[entry.identifier];
                                if (!draft || draft.storeId === "") {
                                  return "";
                                }
                                return String(draft.storeId);
                              })()}
                              onChange={(event) =>
                                handleDistributionDraftChange(
                                  entry.identifier,
                                  "storeId",
                                  event.target.value === ""
                                    ? ""
                                    : Number.parseInt(event.target.value, 10),
                                )
                              }
                            >
                              <option value="">Selecciona sucursal</option>
                              {destinationStores.map((store) => (
                                <option key={`${entry.identifier}-${store.id}`} value={store.id}>
                                  {store.name}
                                </option>
                              ))}
                            </select>
                            <input
                              type="number"
                              min={1}
                              step={1}
                              value={(
                                distributionDrafts[entry.identifier]?.quantity ?? 1
                              ).toString()}
                              onChange={(event) =>
                                handleDistributionDraftChange(
                                  entry.identifier,
                                  "quantity",
                                  Number.parseInt(event.target.value, 10) || 1,
                                )
                              }
                              aria-label={`Cantidad a transferir para ${entry.identifier}`}
                            />
                            <button
                              type="button"
                              className="ghost"
                              onClick={() => handleAddDistribution(entry.identifier)}
                            >
                              Asignar
                            </button>
                          </div>
                        ) : (
                          <p className="muted-text">
                            Registra más sucursales para distribuir inventario.
                          </p>
                        )}
                      </div>
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
            {result.processed.length} elementos registrados · {result.totals.total_quantity}{" "}
            unidades.
          </p>
          <ul className="receipt-list">
            {result.processed.map((item) => (
              <li key={`${item.identifier}-${item.device_id}`}>
                <strong>{item.identifier}</strong> — movimiento #{item.movement.id} en{" "}
                {item.movement.sucursal_destino ?? "sucursal"}
              </li>
            ))}
          </ul>
          {result.auto_transfers?.length ? (
            <div className="auto-transfer-list">
              <h4>Transferencias automáticas generadas</h4>
              <ul>
                {result.auto_transfers.map((transfer: TransferOrder) => (
                  <li key={transfer.id}>
                    Transferencia #{transfer.id} →{" "}
                    {storeLookup.get(transfer.destination_store_id) ??
                      `Sucursal #${transfer.destination_store_id}`}{" "}
                    · Estado: {transfer.status}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}

export default ReceivingPanel;
