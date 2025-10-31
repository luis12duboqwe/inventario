import type { SalesFiltersProps } from "./types";

function FiltersPanel({
  stores,
  customers,
  users,
  filters,
  exportReason,
  isExporting,
  onFiltersChange,
  onExportReasonChange,
  onExportPdf,
  onExportExcel,
  onClearFilters,
}: SalesFiltersProps) {
  return (
    <div className="section-divider">
      <h3>Listado general de ventas</h3>
      <div className="form-grid">
        <label>
          Sucursal
          <select
            value={filters.storeId ?? ""}
            onChange={(event) =>
              onFiltersChange({ storeId: event.target.value ? Number(event.target.value) : null })
            }
          >
            <option value="">Todas las sucursales</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Cliente
          <select
            value={filters.customerId ?? ""}
            onChange={(event) =>
              onFiltersChange({ customerId: event.target.value ? Number(event.target.value) : null })
            }
          >
            <option value="">Todos los clientes</option>
            {customers.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Usuario
          <select
            value={filters.userId ?? ""}
            onChange={(event) =>
              onFiltersChange({ userId: event.target.value ? Number(event.target.value) : null })
            }
          >
            <option value="">Todos los usuarios</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name ?? user.username}
              </option>
            ))}
          </select>
        </label>

        <label>
          Desde
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(event) => onFiltersChange({ dateFrom: event.target.value })}
          />
        </label>

        <label>
          Hasta
          <input
            type="date"
            value={filters.dateTo}
            onChange={(event) => onFiltersChange({ dateTo: event.target.value })}
          />
        </label>

        <label className="span-2">
          Buscar por IMEI, SKU o modelo
          <input
            value={filters.query}
            onChange={(event) => onFiltersChange({ query: event.target.value })}
            placeholder="Ej. IMEI, SKU, modelo o palabra clave"
          />
        </label>
      </div>

      <div className="form-grid">
        <label className="span-2">
          Motivo corporativo para exportar
          <input
            value={exportReason}
            onChange={(event) => onExportReasonChange(event.target.value)}
            placeholder="Ej. Reporte diario ventas"
          />
        </label>
        <div className="button-row">
          <button type="button" className="btn btn--secondary" onClick={onExportPdf} disabled={isExporting}>
            {isExporting ? "Generando..." : "Exportar PDF"}
          </button>
          <button type="button" className="btn btn--secondary" onClick={onExportExcel} disabled={isExporting}>
            {isExporting ? "Generando..." : "Exportar Excel"}
          </button>
          <button type="button" className="btn btn--ghost" onClick={onClearFilters}>
            Limpiar filtros
          </button>
        </div>
      </div>
    </div>
  );
}

export default FiltersPanel;
