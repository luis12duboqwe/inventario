import { useEffect, useMemo, useState } from "react";

import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import { listRepairOrders, type RepairOrder } from "../../../api";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

const STATUS_LABELS: Record<RepairOrder["status"], string> = {
  PENDIENTE: "Pendiente",
  EN_PROCESO: "En proceso",
  LISTO: "Listo para entrega",
  ENTREGADO: "Entregado",
};

function RepairsBudgetsPage() {
  const { token, stores, selectedStoreId, setSelectedStoreId } = useRepairsLayout();
  const [orders, setOrders] = useState<RepairOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<RepairOrder["status"] | "TODOS">("TODOS");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const fetchBudgets = async () => {
      if (!selectedStoreId) {
        setOrders([]);
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const data = await listRepairOrders(token, { store_id: selectedStoreId, limit: 200 });
        setOrders(data);
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible cargar los presupuestos de reparación.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void fetchBudgets();
  }, [refreshKey, selectedStoreId, token]);

  const filteredOrders = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();
    return orders.filter((order) => {
      if (statusFilter !== "TODOS" && order.status !== statusFilter) {
        return false;
      }
      if (!normalized) {
        return true;
      }
      const haystack = `${order.id} ${order.customer_name ?? "Mostrador"} ${order.technician_name} ${order.damage_type}`.toLowerCase();
      return haystack.includes(normalized);
    });
  }, [orders, searchTerm, statusFilter]);

  const summary = useMemo(() => {
    const totals = filteredOrders.reduce(
      (acc, order) => {
        const total = Number(order.total_cost ?? 0);
        acc.totalCost += total;
        if (order.status === "PENDIENTE" || order.status === "EN_PROCESO") {
          acc.pending += 1;
        }
        if (order.status === "LISTO" || order.status === "ENTREGADO") {
          acc.finalized += 1;
        }
        return acc;
      },
      { totalCost: 0, pending: 0, finalized: 0 },
    );
    const average = filteredOrders.length > 0 ? totals.totalCost / filteredOrders.length : 0;
    return { ...totals, average };
  }, [filteredOrders]);

  return (
    <div className="repairs-subpage">
      <PageHeader
        title="Presupuestos y estimados"
        subtitle="Analiza el valor comprometido por las reparaciones y prioriza entregas pendientes."
        actions={[
          {
            id: "refresh-budgets",
            label: "Actualizar datos",
            onClick: () => setRefreshKey((value) => value + 1),
            variant: "ghost",
          },
        ]}
      />

      <PageToolbar
        onSearch={setSearchTerm}
        searchPlaceholder="Buscar presupuesto por cliente, folio o técnico"
      >
        <div className="toolbar-inline-fields">
          <label>
            Sucursal
            <select
              value={selectedStoreId ?? ""}
              onChange={(event) => {
                const value = event.target.value ? Number(event.target.value) : null;
                setSelectedStoreId(value);
              }}
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
            Estado
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as RepairOrder["status"] | "TODOS")}
            >
              <option value="TODOS">Todos</option>
              {Object.keys(STATUS_LABELS).map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABELS[status as RepairOrder["status"]]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </PageToolbar>

      {selectedStoreId ? (
        <>
          <section className="card metrics-grid">
            <article className="metric">
              <h3>Total estimado</h3>
              <strong>${summary.totalCost.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </article>
            <article className="metric">
              <h3>Órdenes pendientes</h3>
              <strong>{summary.pending}</strong>
            </article>
            <article className="metric">
              <h3>Órdenes finalizadas</h3>
              <strong>{summary.finalized}</strong>
            </article>
            <article className="metric">
              <h3>Promedio por reparación</h3>
              <strong>${summary.average.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </article>
          </section>

          <section className="card wide">
            <h2>Listado de presupuestos</h2>
            {loading ? <p className="muted-text">Cargando presupuestos…</p> : null}
            {error ? <div className="alert error">{error}</div> : null}
            {!loading && !error && filteredOrders.length === 0 ? (
              <p className="muted-text">No hay presupuestos que coincidan con los filtros seleccionados.</p>
            ) : null}
            {!loading && !error && filteredOrders.length > 0 ? (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Folio</th>
                      <th>Cliente</th>
                      <th>Técnico</th>
                      <th>Diagnóstico</th>
                      <th>Estado</th>
                      <th>Valor</th>
                      <th>Actualizado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredOrders.map((order) => (
                      <tr key={order.id}>
                        <td>#{order.id}</td>
                        <td>{order.customer_name ?? "Mostrador"}</td>
                        <td>{order.technician_name}</td>
                        <td>{order.damage_type}</td>
                        <td>{STATUS_LABELS[order.status]}</td>
                        <td>${Number(order.total_cost ?? 0).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td>{new Date(order.updated_at).toLocaleString("es-MX")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        </>
      ) : (
        <section className="card">
          <p className="muted-text">Selecciona una sucursal para revisar los presupuestos de reparación.</p>
        </section>
      )}
    </div>
  );
}

export default RepairsBudgetsPage;
