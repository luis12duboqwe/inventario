import { FormEvent, useMemo, useState } from "react";

import { useInventoryLayout } from "./context/InventoryLayoutContext";
import { promptCorporateReason } from "../../../utils/corporateReason";
import type { InventoryReservation } from "@api/inventory";

function formatDateTime(value: string): string {
  if (!value) {
    return "-";
  }
  try {
    return new Date(value).toLocaleString("es-HN", {
      hour12: false,
    });
  } catch {
    return value;
  }
}

function toInputValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function parseDateInput(value: string): string | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

function ReservationStatusBadge({ reservation }: { reservation: InventoryReservation }) {
  const variant =
    reservation.status === "RESERVADO"
      ? "badge--info"
      : reservation.status === "CONSUMIDO"
      ? "badge--success"
      : reservation.status === "CANCELADO"
      ? "badge--muted"
      : "badge--warning";
  return <span className={`badge ${variant}`}>{reservation.status}</span>;
}

const DEFAULT_REASON_CREATE = "Reserva temporal de inventario";

function InventoryReservationsPage(): JSX.Element {
  const {
    module: { devices, selectedStoreId },
    reservations,
  } = useInventoryLayout();
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1);
  const [expiresAt, setExpiresAt] = useState(() => {
    const defaultDate = new Date(Date.now() + 2 * 60 * 60 * 1000);
    return toInputValue(defaultDate);
  });
  const [creating, setCreating] = useState(false);
  const [actingReservationId, setActingReservationId] = useState<number | null>(null);

  const availableDevices = useMemo(
    () => devices.filter((device) => device.quantity > 0),
    [devices],
  );

  const handleSubmitReservation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedStoreId) {
      return;
    }
    if (selectedDeviceId === "") {
      return;
    }
    const isoExpires = parseDateInput(expiresAt);
    if (!isoExpires) {
      alert("Ingresa una fecha de expiración válida en formato AAAA-MM-DD HH:MM");
      return;
    }
    const reason = promptCorporateReason(DEFAULT_REASON_CREATE);
    if (!reason) {
      return;
    }
    setCreating(true);
    try {
      await reservations.create(
        {
          device_id: selectedDeviceId,
          quantity,
          expires_at: isoExpires,
        },
        reason,
      );
      const nextDefault = new Date(Date.now() + 2 * 60 * 60 * 1000);
      setExpiresAt(toInputValue(nextDefault));
      setQuantity(1);
    } finally {
      setCreating(false);
    }
  };

  const handleRenew = async (reservation: InventoryReservation) => {
    const defaultValue = toInputValue(
      new Date(new Date(reservation.expires_at).getTime() + 60 * 60 * 1000),
    );
    const newExpiration = window.prompt(
      "Nueva fecha y hora de expiración (formato AAAA-MM-DDTHH:MM)",
      defaultValue,
    );
    if (!newExpiration) {
      return;
    }
    const isoExpires = parseDateInput(newExpiration);
    if (!isoExpires) {
      alert("No se pudo interpretar la nueva fecha de expiración.");
      return;
    }
    const reason = promptCorporateReason(`Renovar reserva #${reservation.id}`);
    if (!reason) {
      return;
    }
    setActingReservationId(reservation.id);
    try {
      await reservations.renew(reservation.id, { expires_at: isoExpires }, reason);
    } finally {
      setActingReservationId(null);
    }
  };

  const handleCancel = async (reservation: InventoryReservation) => {
    const confirmed = window.confirm(
      "¿Deseas liberar la reserva y devolver las unidades al inventario?",
    );
    if (!confirmed) {
      return;
    }
    const reason = promptCorporateReason(`Cancelar reserva #${reservation.id}`);
    if (!reason) {
      return;
    }
    setActingReservationId(reservation.id);
    try {
      await reservations.cancel(reservation.id, reason);
    } finally {
      setActingReservationId(null);
    }
  };

  const handleToggleIncludeExpired = async () => {
    reservations.setIncludeExpired(!reservations.includeExpired);
    await reservations.refresh(1);
  };

  const handleChangePage = async (page: number) => {
    await reservations.refresh(page);
  };

  return (
    <div className="inventory-reservations">
      <section className="panel">
        <header className="panel__header">
          <div>
            <h2 className="panel__title">Reservas de inventario</h2>
            <p className="panel__subtitle">
              Bloquea unidades críticas antes de confirmar ventas o transferencias. Las reservas se
              liberan automáticamente al expirar.
            </p>
          </div>
          <div className="panel__actions">
            <label className="toggle">
              <input
                type="checkbox"
                checked={reservations.includeExpired}
                onChange={handleToggleIncludeExpired}
              />
              <span>Mostrar vencidas</span>
            </label>
          </div>
        </header>
        {reservations.expiringSoon.length > 0 && (
          <div className="alert alert--warning" role="status">
            <strong>{reservations.expiringSoon.length}</strong> reservas vencerán en los próximos 30
            minutos.
          </div>
        )}
        <form className="reservation-form" onSubmit={handleSubmitReservation}>
          <fieldset disabled={!selectedStoreId || creating}>
            <legend>Crear nueva reserva</legend>
            <div className="form-grid">
              <label className="form-field">
                <span>Producto</span>
                <select
                  value={selectedDeviceId}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelectedDeviceId(value ? Number(value) : "");
                  }}
                  required
                >
                  <option value="">Selecciona un dispositivo</option>
                  {availableDevices.map((device) => (
                    <option key={device.id} value={device.id}>
                      {device.sku} — {device.name} (stock {device.quantity})
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>Cantidad</span>
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(event) => setQuantity(Number(event.target.value))}
                  required
                />
              </label>
              <label className="form-field">
                <span>Expira</span>
                <input
                  type="datetime-local"
                  value={expiresAt}
                  onChange={(event) => setExpiresAt(event.target.value)}
                  required
                />
              </label>
            </div>
            <button type="submit" className="button button--primary" disabled={creating}>
              {creating ? "Reservando…" : "Reservar unidades"}
            </button>
          </fieldset>
        </form>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Estado</th>
                <th>Expira</th>
                <th>Motivo</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {reservations.items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center">
                    {reservations.loading ? "Cargando reservas…" : "No hay reservas registradas."}
                  </td>
                </tr>
              ) : (
                reservations.items.map((reservation) => {
                  const device =
                    reservation.device ?? devices.find((item) => item.id === reservation.device_id);
                  const canManage = reservation.status === "RESERVADO";
                  const working = actingReservationId === reservation.id;
                  return (
                    <tr key={reservation.id}>
                      <td>
                        <div className="cell-main">
                          <strong>{device?.sku ?? `ID ${reservation.device_id}`}</strong>
                          <small>{device?.name ?? "Dispositivo"}</small>
                        </div>
                      </td>
                      <td>{reservation.quantity}</td>
                      <td>
                        <ReservationStatusBadge reservation={reservation} />
                      </td>
                      <td>{formatDateTime(reservation.expires_at)}</td>
                      <td>{reservation.reason}</td>
                      <td className="table-actions">
                        <button
                          type="button"
                          className="button button--ghost"
                          onClick={() => handleRenew(reservation)}
                          disabled={!canManage || working}
                        >
                          Renovar
                        </button>
                        <button
                          type="button"
                          className="button button--danger"
                          onClick={() => handleCancel(reservation)}
                          disabled={!canManage || working}
                        >
                          Cancelar
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        <footer className="table-footer">
          <div>
            Página {reservations.meta.page} de {Math.max(reservations.meta.pages, 1)} —{" "}
            {reservations.meta.total} reservas
          </div>
          <div className="table-pagination">
            <button
              type="button"
              className="button button--ghost"
              onClick={() => handleChangePage(Math.max(reservations.meta.page - 1, 1))}
              disabled={reservations.meta.page <= 1 || reservations.loading}
            >
              Anterior
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={() =>
                handleChangePage(
                  Math.min(reservations.meta.page + 1, Math.max(reservations.meta.pages, 1)),
                )
              }
              disabled={reservations.meta.page >= reservations.meta.pages || reservations.loading}
            >
              Siguiente
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}

export default InventoryReservationsPage;
