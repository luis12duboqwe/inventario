import { useEffect, useMemo, useState } from "react";
import type {
  OperationsHistoryRecord,
  OperationsTechnicianSummary,
  Store,
} from "../../../api";
import { listOperationsHistory } from "../../../api";

import { useDashboard } from "../../dashboard/context/DashboardContext";

const OPERATION_TYPES: Array<{ id: OperationsHistoryRecord["operation_type"]; label: string }> = [
  { id: "purchase", label: "Compra" },
  { id: "sale", label: "Venta" },
  { id: "transfer_dispatch", label: "Transferencia despachada" },
  { id: "transfer_receive", label: "Transferencia recibida" },
];

type HistoryFilter = {
  storeId: number | "all";
  type: OperationsHistoryRecord["operation_type"] | "all";
  technicianId: number | "all";
  startDate: string;
  endDate: string;
};

type Props = {
  token: string;
  stores: Store[];
};

const formatDateInput = (date: Date): string => date.toISOString().slice(0, 10);

function OperationsHistoryPanel({ stores, token }: Props) {
  const { formatCurrency } = useDashboard();
  const today = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 14);

  const [filters, setFilters] = useState<HistoryFilter>({
    storeId: "all",
    type: "all",
    technicianId: "all",
    startDate: formatDateInput(start),
    endDate: formatDateInput(today),
  });
  const [records, setRecords] = useState<OperationsHistoryRecord[]>([]);
  const [technicians, setTechnicians] = useState<OperationsTechnicianSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await listOperationsHistory(token, {
          storeId: filters.storeId === "all" ? undefined : filters.storeId,
          technicianId: filters.technicianId === "all" ? undefined : filters.technicianId,
          startDate: filters.startDate,
          endDate: filters.endDate,
        });
        if (!cancelled) {
          setRecords(response.records);
          setTechnicians(response.technicians);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "No fue posible cargar el historial de operaciones",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchHistory();
    return () => {
      cancelled = true;
    };
  }, [token, filters.storeId, filters.technicianId, filters.startDate, filters.endDate]);

  const filteredRecords = useMemo(() => {
    return records.filter((record) => filters.type === "all" || record.operation_type === filters.type);
  }, [records, filters.type]);

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Historial corporativo</h2>
          <p className="card-subtitle">Últimas operaciones consolidadas para consulta rápida.</p>
        </div>
      </header>
      <form className="form-grid">
        <label>
          <span>Sucursal</span>
          <select
            value={filters.storeId === "all" ? "all" : String(filters.storeId)}
            onChange={(event) => {
              const value = event.target.value;
              setFilters((current) => ({
                ...current,
                storeId: value === "all" ? "all" : Number(value),
              }));
            }}
          >
            <option value="all">Todas</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Tipo de operación</span>
          <select
            value={filters.type}
            onChange={(event) => {
              const value = event.target.value as HistoryFilter["type"];
              setFilters((current) => ({
                ...current,
                type: value,
              }));
            }}
          >
            <option value="all">Todas</option>
            {OPERATION_TYPES.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Técnico</span>
          <select
            value={filters.technicianId === "all" ? "all" : String(filters.technicianId)}
            onChange={(event) => {
              const value = event.target.value;
              setFilters((current) => ({
                ...current,
                technicianId: value === "all" ? "all" : Number(value),
              }));
            }}
          >
            <option value="all">Todos</option>
            {technicians.map((technician) => (
              <option key={technician.id} value={technician.id}>
                {technician.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Desde</span>
          <input
            type="date"
            value={filters.startDate}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                startDate: event.target.value,
              }))
            }
          />
        </label>
        <label>
          <span>Hasta</span>
          <input
            type="date"
            value={filters.endDate}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                endDate: event.target.value,
              }))
            }
          />
        </label>
      </form>
      {error ? <div className="alert error">{error}</div> : null}
      <div className="section-divider">
        <h3>Últimos movimientos</h3>
        {loading ? <p className="muted-text">Cargando historial…</p> : null}
        {filteredRecords.length === 0 && !loading ? (
          <p className="muted-text">No hay operaciones que coincidan con los filtros seleccionados.</p>
        ) : null}
        {filteredRecords.length > 0 ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Sucursal</th>
                  <th scope="col">Tipo</th>
                  <th scope="col">Técnico</th>
                  <th scope="col">Referencia</th>
                  <th scope="col">Descripción</th>
                  <th scope="col">Total</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((record) => {
                  const storeName = record.store_id
                    ? stores.find((store) => store.id === record.store_id)?.name ?? "Desconocida"
                    : "Corporativo";
                  const typeLabel =
                    OPERATION_TYPES.find((option) => option.id === record.operation_type)?.label ??
                    record.operation_type;
                  const technicianName = record.technician_name ?? "Sin asignar";
                  const formattedAmount =
                    record.amount != null ? formatCurrency(record.amount) : "—";
                  return (
                    <tr key={record.id}>
                      <td data-label="Fecha">{new Date(record.occurred_at).toLocaleString("es-MX")}</td>
                      <td data-label="Sucursal">{storeName}</td>
                      <td data-label="Tipo">{typeLabel}</td>
                      <td data-label="Técnico">{technicianName}</td>
                      <td data-label="Referencia">{record.reference ?? "—"}</td>
                      <td data-label="Descripción">{record.description}</td>
                      <td data-label="Total">{formattedAmount}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </section>
  );
}

export default OperationsHistoryPanel;
