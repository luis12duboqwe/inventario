import { useEffect, useMemo, useState } from "react";
import type { Store } from "@api/stores";
import type { TransferOrder } from "@api/transfers";
import {
  cancelTransferOrder,
  createTransferOrder,
  dispatchTransferOrder,
  listTransfers,
  receiveTransferOrder,
} from "@api/transfers";
import Button from "@components/ui/Button";
import Modal from "@components/ui/Modal";

const statusLabels: Record<TransferOrder["status"], string> = {
  SOLICITADA: "Solicitada",
  EN_TRANSITO: "En tránsito",
  RECIBIDA: "Recibida",
  CANCELADA: "Cancelada",
};

type Props = {
  token: string;
  stores: Store[];
  defaultOriginId?: number | null;
  onRefreshInventory?: () => void;
};

type TransferForm = {
  originStoreId: number | null;
  destinationStoreId: number | null;
  deviceId: number;
  quantity: number;
  reason: string;
};

const initialForm: TransferForm = {
  originStoreId: null,
  destinationStoreId: null,
  deviceId: 0,
  quantity: 1,
  reason: "",
};

function TransferOrders({ token, stores, defaultOriginId = null, onRefreshInventory }: Props) {
  const [transfers, setTransfers] = useState<TransferOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<TransferForm>({
    ...initialForm,
    originStoreId: defaultOriginId,
  });
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [transitionDialog, setTransitionDialog] = useState<{
    action: "dispatch" | "receive" | "cancel";
    transfer: TransferOrder;
  } | null>(null);
  const [transitionReason, setTransitionReason] = useState("");
  const [transitionError, setTransitionError] = useState<string | null>(null);
  const [transitionSubmitting, setTransitionSubmitting] = useState(false);

  const transitionTitles: Record<"dispatch" | "receive" | "cancel", string> = {
    dispatch: "Despachar transferencia",
    receive: "Recibir transferencia",
    cancel: "Cancelar transferencia",
  };

  const transitionSuccessMessages: Record<"dispatch" | "receive" | "cancel", string> = {
    dispatch: "La transferencia fue despachada correctamente.",
    receive: "La transferencia fue recibida correctamente.",
    cancel: "La transferencia fue cancelada correctamente.",
  };

  const sortedTransfers = useMemo(() => {
    return [...transfers].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }, [transfers]);

  const refreshTransfers = async (storeId?: number | null) => {
    try {
      setLoading(true);
      const data = await listTransfers(token, storeId ?? undefined);
      setTransfers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible cargar las transferencias");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshTransfers(form.originStoreId ?? undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.originStoreId, token]);

  useEffect(() => {
    setForm((current) => ({ ...current, originStoreId: defaultOriginId ?? null }));
  }, [defaultOriginId]);

  const updateForm = (updates: Partial<TransferForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.originStoreId || !form.destinationStoreId) {
      setError("Selecciona sucursales de origen y destino.");
      return;
    }
    if (form.originStoreId === form.destinationStoreId) {
      setError("El origen y destino deben ser diferentes.");
      return;
    }
    const trimmedReason = form.reason.trim();
    if (trimmedReason.length < 5) {
      setError("Indica un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    try {
      setError(null);
      await createTransferOrder(
        token,
        {
          origin_store_id: form.originStoreId,
          destination_store_id: form.destinationStoreId,
          reason: trimmedReason,
          items: [{ device_id: form.deviceId, quantity: form.quantity }],
        },
        trimmedReason,
      );
      setMessage("Transferencia registrada correctamente");
      setForm({ ...initialForm, originStoreId: form.originStoreId });
      await refreshTransfers(form.originStoreId);
      onRefreshInventory?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible crear la transferencia");
    }
  };

  const handleTransition = (action: "dispatch" | "receive" | "cancel", transfer: TransferOrder) => {
    setTransitionDialog({ action, transfer });
    setTransitionReason("");
    setTransitionError(null);
  };

  const closeTransitionDialog = () => {
    if (transitionSubmitting) {
      return;
    }
    setTransitionDialog(null);
    setTransitionReason("");
    setTransitionError(null);
  };

  const submitTransition = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!transitionDialog) {
      return;
    }
    const normalizedReason = transitionReason.trim();
    if (normalizedReason.length < 5) {
      setTransitionError("Ingresa un motivo corporativo de al menos 5 caracteres.");
      return;
    }

    try {
      setTransitionSubmitting(true);
      setTransitionError(null);
      setError(null);

      const { action, transfer } = transitionDialog;
      if (action === "dispatch") {
        await dispatchTransferOrder(
          token,
          transfer.id,
          { reason: normalizedReason },
          normalizedReason,
        );
      } else if (action === "receive") {
        await receiveTransferOrder(
          token,
          transfer.id,
          { reason: normalizedReason },
          normalizedReason,
        );
      } else {
        await cancelTransferOrder(
          token,
          transfer.id,
          { reason: normalizedReason },
          normalizedReason,
        );
      }

      await refreshTransfers(form.originStoreId);
      onRefreshInventory?.();
      setMessage(transitionSuccessMessages[transitionDialog.action]);
      closeTransitionDialog();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "No fue posible actualizar la transferencia";
      setTransitionError(message);
    } finally {
      setTransitionSubmitting(false);
    }
  };

  return (
    <section className="panel">
      <header className="panel__header">
        <h2>Transferencias entre tiendas</h2>
        <p className="panel__subtitle">
          Controla las órdenes de traslado entre sucursales con permisos específicos por tienda.
        </p>
      </header>
      <div className="panel__body">
        {error && <div className="alert error">{error}</div>}
        {message && <div className="alert success">{message}</div>}
        <form className="transfer-form" onSubmit={handleSubmit}>
          <div className="form-grid">
            <label>
              Origen
              <select
                value={form.originStoreId ?? ""}
                onChange={(event) =>
                  updateForm({ originStoreId: Number(event.target.value) || null })
                }
              >
                <option value="">Selecciona una sucursal</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Destino
              <select
                value={form.destinationStoreId ?? ""}
                onChange={(event) =>
                  updateForm({ destinationStoreId: Number(event.target.value) || null })
                }
              >
                <option value="">Selecciona una sucursal</option>
                {stores
                  .filter((store) => store.id !== form.originStoreId)
                  .map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              ID de dispositivo
              <input
                type="number"
                min={1}
                value={form.deviceId || ""}
                onChange={(event) => updateForm({ deviceId: Number(event.target.value) })}
              />
            </label>
            <label>
              Cantidad
              <input
                type="number"
                min={1}
                value={form.quantity}
                onChange={(event) => updateForm({ quantity: Number(event.target.value) })}
              />
            </label>
            <label className="form-span">
              Motivo
              <input
                type="text"
                value={form.reason}
                onChange={(event) => updateForm({ reason: event.target.value })}
                placeholder="Motivo operativo"
                minLength={5}
                required
              />
            </label>
          </div>
          <button type="submit" className="btn btn--primary">
            Registrar transferencia
          </button>
        </form>

        <div className="transfer-list">
          <h3>Historial reciente</h3>
          {loading ? (
            <p>Cargando transferencias…</p>
          ) : sortedTransfers.length === 0 ? (
            <p>No hay transferencias registradas.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Origen</th>
                  <th>Destino</th>
                  <th>Estatus</th>
                  <th>Actualización</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {sortedTransfers.map((transfer) => (
                  <tr key={transfer.id}>
                    <td>#{transfer.id}</td>
                    <td>{transfer.origin_store_id}</td>
                    <td>{transfer.destination_store_id}</td>
                    <td>{statusLabels[transfer.status]}</td>
                    <td>{new Date(transfer.updated_at).toLocaleString()}</td>
                    <td>
                      <div className="transfer-actions">
                        {transfer.status === "SOLICITADA" && (
                          <button
                            type="button"
                            className="btn btn--ghost"
                            onClick={() => handleTransition("dispatch", transfer)}
                          >
                            Despachar
                          </button>
                        )}
                        {transfer.status !== "CANCELADA" && transfer.status !== "RECIBIDA" && (
                          <button
                            type="button"
                            className="btn btn--primary"
                            onClick={() => handleTransition("receive", transfer)}
                          >
                            Recibir
                          </button>
                        )}
                        {(["SOLICITADA", "EN_TRANSITO"] as TransferOrder["status"][]).includes(
                          transfer.status,
                        ) ? (
                          <button
                            type="button"
                            className="btn btn--danger"
                            onClick={() => handleTransition("cancel", transfer)}
                          >
                            Cancelar
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      <Modal
        open={transitionDialog != null}
        title={transitionDialog ? transitionTitles[transitionDialog.action] : "Motivo corporativo"}
        description="Describe el motivo corporativo que sustenta la operación."
        onClose={closeTransitionDialog}
        dismissDisabled={transitionSubmitting}
        footer={
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={closeTransitionDialog}
              disabled={transitionSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" form="transfer-transition-form" disabled={transitionSubmitting}>
              {transitionSubmitting ? "Aplicando…" : "Confirmar"}
            </Button>
          </>
        }
      >
        <form id="transfer-transition-form" className="form-grid" onSubmit={submitTransition}>
          {transitionDialog ? (
            <p className="form-span muted-text">
              Transferencia #{transitionDialog.transfer.id} ·{" "}
              {statusLabels[transitionDialog.transfer.status]}
            </p>
          ) : null}
          <label className="form-span">
            <span>Motivo corporativo</span>
            <textarea
              value={transitionReason}
              onChange={(event) => setTransitionReason(event.target.value)}
              placeholder="Detalla el motivo corporativo"
              minLength={5}
              required
              rows={3}
            />
          </label>
          <p className="form-span muted-text">
            El motivo se registrará en la bitácora y quedará ligado a la transferencia.
          </p>
          {transitionError ? <p className="form-span alert error">{transitionError}</p> : null}
        </form>
      </Modal>
    </section>
  );
}

export default TransferOrders;
