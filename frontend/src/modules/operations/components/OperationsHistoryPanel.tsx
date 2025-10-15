import { useMemo, useState } from "react";
import type { Store } from "../../../api";

import { useDashboard } from "../../dashboard/context/DashboardContext";

type OperationType = "venta" | "compra" | "transferencia" | "ajuste";

type HistoryFilter = {
  storeId: number | "all";
  type: OperationType | "all";
};

type HistoryRecord = {
  id: string;
  storeId: number | null;
  type: OperationType;
  reference: string;
  notes: string;
  createdAt: Date;
  total: number;
};

type Props = {
  stores: Store[];
};

const OPERATION_TYPES: Array<{ id: OperationType; label: string }> = [
  { id: "venta", label: "Venta" },
  { id: "compra", label: "Compra" },
  { id: "transferencia", label: "Transferencia" },
  { id: "ajuste", label: "Ajuste" },
];

const createMockRecords = (stores: Store[]): HistoryRecord[] => {
  const now = Date.now();
  return stores.slice(0, 3).flatMap((store, index) => [
    {
      id: `${store.id}-venta`,
      storeId: store.id,
      type: "venta" as const,
      reference: `VNT-${store.id}-${index + 1}`,
      notes: "Ticket generado desde POS híbrido",
      createdAt: new Date(now - index * 3600 * 1000),
      total: 15450 + index * 2200,
    },
    {
      id: `${store.id}-compra`,
      storeId: store.id,
      type: "compra" as const,
      reference: `CMP-${store.id}-${index + 1}`,
      notes: "Recepción parcial registrada",
      createdAt: new Date(now - (index + 1) * 5400 * 1000),
      total: 24500 + index * 1800,
    },
  ]);
};

function OperationsHistoryPanel({ stores }: Props) {
  const { formatCurrency } = useDashboard();
  const [filters, setFilters] = useState<HistoryFilter>({ storeId: "all", type: "all" });
  const [records] = useState<HistoryRecord[]>(() => createMockRecords(stores));

  const filteredRecords = useMemo(() => {
    return records.filter((record) => {
      const matchesStore = filters.storeId === "all" || record.storeId === filters.storeId;
      const matchesType = filters.type === "all" || record.type === filters.type;
      return matchesStore && matchesType;
    });
  }, [filters, records]);

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
              const value = event.target.value as OperationType | "all";
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
      </form>
      <div className="section-divider">
        <h3>Últimos movimientos</h3>
        {filteredRecords.length === 0 ? (
          <p className="muted-text">No hay operaciones que coincidan con los filtros seleccionados.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Sucursal</th>
                  <th scope="col">Tipo</th>
                  <th scope="col">Referencia</th>
                  <th scope="col">Notas</th>
                  <th scope="col">Total</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((record) => {
                  const storeName = record.storeId
                    ? stores.find((store) => store.id === record.storeId)?.name ?? "Desconocida"
                    : "Corporativo";
                  const typeLabel = OPERATION_TYPES.find((option) => option.id === record.type)?.label ?? record.type;
                  return (
                    <tr key={record.id}>
                      <td data-label="Fecha">{record.createdAt.toLocaleString("es-MX")}</td>
                      <td data-label="Sucursal">{storeName}</td>
                      <td data-label="Tipo">{typeLabel}</td>
                      <td data-label="Referencia">{record.reference}</td>
                      <td data-label="Notas">{record.notes}</td>
                      <td data-label="Total">{formatCurrency(record.total)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default OperationsHistoryPanel;
