import { useEffect, useMemo, useState } from "react";

import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import type { PageHeaderAction } from "../../../components/layout/PageHeader";
import { getDevices, listRepairOrders, type RepairOrder } from "../../../api";
import { useRepairsLayout } from "./context/RepairsLayoutContext";

type PartSummary = {
  deviceId: number;
  deviceLabel: string;
  totalQuantity: number;
  totalCost: number;
  usageCount: number;
};

function RepairsPartsPage() {
  const { token, stores, selectedStoreId, setSelectedStoreId, onInventoryRefresh } = useRepairsLayout();
  const [summaries, setSummaries] = useState<PartSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const fetchParts = async () => {
      if (!selectedStoreId) {
        setSummaries([]);
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const [orders, devices] = await Promise.all([
          listRepairOrders(token, { store_id: selectedStoreId, limit: 200 }),
          getDevices(token, selectedStoreId),
        ]);
        const devicesById = new Map(devices.map((device) => [device.id, `${device.sku} · ${device.name}`]));
        const aggregate = new Map<number, PartSummary>();
        orders.forEach((order: RepairOrder) => {
          order.parts.forEach((part) => {
            if (!part.device_id) {
              return;
            }
            const current = aggregate.get(part.device_id) ?? {
              deviceId: part.device_id,
              deviceLabel: devicesById.get(part.device_id) ?? `Dispositivo #${part.device_id}`,
              totalQuantity: 0,
              totalCost: 0,
              usageCount: 0,
            };
            current.totalQuantity += part.quantity;
            current.totalCost += part.quantity * part.unit_cost;
            current.usageCount += 1;
            aggregate.set(part.device_id, current);
          });
        });
        setSummaries(Array.from(aggregate.values()).sort((a, b) => b.totalQuantity - a.totalQuantity));
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible obtener el uso de repuestos.";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void fetchParts();
  }, [refreshKey, selectedStoreId, token]);

  const filteredSummaries = useMemo(() => {
    if (!searchTerm.trim()) {
      return summaries;
    }
    const normalized = searchTerm.trim().toLowerCase();
    return summaries.filter((summary) => summary.deviceLabel.toLowerCase().includes(normalized));
  }, [summaries, searchTerm]);

  const headerActions: PageHeaderAction[] = onInventoryRefresh
    ? [
        {
          id: "refresh-inventory",
          label: "Actualizar inventario",
          onClick: () => {
            void onInventoryRefresh();
            setRefreshKey((value) => value + 1);
          },
          variant: "ghost",
        },
      ]
    : [
        {
          id: "refresh-data",
          label: "Actualizar datos",
          onClick: () => setRefreshKey((value) => value + 1),
          variant: "ghost",
        },
      ];

  return (
    <div className="repairs-subpage">
      <PageHeader
        title="Consumo de repuestos"
        subtitle="Identifica las piezas más utilizadas en las reparaciones para planear tu reposición."
        actions={headerActions}
      />

      <PageToolbar onSearch={setSearchTerm} searchPlaceholder="Buscar repuesto por nombre o SKU">
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
        </div>
      </PageToolbar>

      {selectedStoreId ? (
        <section className="card wide">
          <h2>Repuestos asociados a reparaciones</h2>
          {loading ? <p className="muted-text">Cargando historial de piezas…</p> : null}
          {error ? <div className="alert error">{error}</div> : null}
          {!loading && !error && filteredSummaries.length === 0 ? (
            <p className="muted-text">No se registran repuestos para las reparaciones con los filtros actuales.</p>
          ) : null}
          {!loading && !error && filteredSummaries.length > 0 ? (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Repuesto</th>
                    <th>Cantidad total</th>
                    <th>Órdenes que lo usan</th>
                    <th>Valor estimado</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSummaries.map((summary) => (
                    <tr key={summary.deviceId}>
                      <td>{summary.deviceLabel}</td>
                      <td>{summary.totalQuantity}</td>
                      <td>{summary.usageCount}</td>
                      <td>${summary.totalCost.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : (
        <section className="card">
          <p className="muted-text">Selecciona una sucursal para revisar el consumo de repuestos.</p>
        </section>
      )}
    </div>
  );
}

export default RepairsPartsPage;
