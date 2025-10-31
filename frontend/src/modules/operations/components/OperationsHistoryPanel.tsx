import { useEffect, useMemo, useState } from "react";
import { Skeleton } from "@/ui/Skeleton"; // [PACK36-operations-history]
import { safeArray, safeDate, safeNumber, safeString } from "@/utils/safeValues"; // [PACK36-operations-history]
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
  const { formatCurrency, pushToast } = useDashboard(); // [PACK36-operations-history]
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

  const normalizedStores = useMemo(() => safeArray(stores), [stores]); // [PACK36-operations-history]

  const formatOccurredAt = (value: unknown) => { // [PACK36-operations-history]
    const parsed = safeDate(value);
    if (!parsed) {
      return "Fecha desconocida";
    }
    return parsed.toLocaleString("es-MX");
  };

  const friendlyErrorMessage = (message: string) => { // [PACK36-operations-history]
    if (message.toLowerCase().includes("failed to fetch")) {
      return "No fue posible conectar con el servicio Softmobile. Intenta nuevamente en unos segundos.";
    }
    return message;
  };

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
          setRecords(safeArray(response?.records)); // [PACK36-operations-history]
          setTechnicians(safeArray(response?.technicians)); // [PACK36-operations-history]
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err instanceof Error
              ? err.message
              : "No fue posible cargar el historial de operaciones";
          const friendly = friendlyErrorMessage(message);
          setError(friendly);
          pushToast({ message: friendly, variant: "error" }); // [PACK36-operations-history]
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
  }, [
    token,
    filters.storeId,
    filters.technicianId,
    filters.startDate,
    filters.endDate,
    pushToast,
  ]);

  const filteredRecords = useMemo(() => {
    return safeArray(records).filter(
      (record) => filters.type === "all" || record.operation_type === filters.type,
    );
  }, [records, filters.type]); // [PACK36-operations-history]

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
            {normalizedStores.map((store) => (
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
        {filteredRecords.length === 0 && !loading ? (
          <p className="muted-text">No hay operaciones que coincidan con los filtros seleccionados.</p>
        ) : null}
        {loading ? (
          <div className="table-wrapper" role="status" aria-busy="true">{/* [PACK36-operations-history] */}
            <Skeleton lines={6} />
          </div>
        ) : filteredRecords.length > 0 ? (
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
                    ? normalizedStores.find((store) => store.id === record.store_id)?.name ?? "Desconocida"
                    : "Corporativo";
                  const typeLabel =
                    OPERATION_TYPES.find((option) => option.id === record.operation_type)?.label ??
                    safeString(record.operation_type, "—");
                  const technicianName = safeString(record.technician_name, "Sin asignar");
                  const formattedAmount = (() => {
                    const amount = safeNumber(record.amount, NaN);
                    return Number.isNaN(amount) ? "—" : formatCurrency(amount);
                  })(); // [PACK36-operations-history]
                  const description = safeString(record.description, "Sin descripción");
                  const reference = safeString(record.reference, "—");
                  return (
                    <tr key={record.id}>
                      <td data-label="Fecha">{formatOccurredAt(record.occurred_at)}</td>
                      <td data-label="Sucursal">{storeName}</td>
                      <td data-label="Tipo">{typeLabel}</td>
                      <td data-label="Técnico">{technicianName}</td>
                      <td data-label="Referencia">{reference}</td>
                      <td data-label="Descripción">{description}</td>
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
