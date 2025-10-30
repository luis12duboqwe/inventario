// [PACK29-*] Filtros interactivos para reportes de ventas
import type { ChangeEvent, FormEvent } from "react";

import Button from "@/shared/components/ui/Button";
import type { Store } from "@/api";

import type { SalesFiltersState } from "../pages/SalesReportsPage";

export type SalesReportsFiltersProps = {
  filters: SalesFiltersState;
  stores: Store[];
  onFiltersChange: (next: SalesFiltersState) => void;
  onRefresh: () => void;
  onExport: () => void;
  loading?: boolean;
  exportDisabled?: boolean;
};

function SalesReportsFilters({
  filters,
  stores,
  onFiltersChange,
  onRefresh,
  onExport,
  loading = false,
  exportDisabled = false,
}: SalesReportsFiltersProps) {
  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = event.target;
    if (name === "branchId") {
      const branchId = value ? Number(value) : null;
      onFiltersChange({ ...filters, branchId });
      return;
    }
    onFiltersChange({ ...filters, [name]: value || null });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onRefresh();
  };

  return (
    <section className="card reports-card" aria-label="Filtros de reportes de ventas">
      <header className="reports-card__header">
        <div>
          <h2>Filtra tu reporte</h2>
          <p className="muted-text">Selecciona el rango de fechas y la sucursal para generar los indicadores.</p>
        </div>
        <form className="reports-card__actions" onSubmit={handleSubmit}>
          <div className="reports-card__filters">
            <label>
              Desde
              <input
                type="date"
                name="from"
                value={filters.from ?? ""}
                onChange={handleChange}
                max={filters.to ?? undefined}
              />
            </label>
            <label>
              Hasta
              <input
                type="date"
                name="to"
                value={filters.to ?? ""}
                onChange={handleChange}
                min={filters.from ?? undefined}
              />
            </label>
            <label>
              Sucursal
              <select name="branchId" value={filters.branchId ?? ""} onChange={handleChange}>
                <option value="">Todas</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="reports-card__downloads">
            <Button type="submit" variant="secondary" size="sm" disabled={loading}>
              {loading ? "Actualizando…" : "Actualizar"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onExport}
              disabled={exportDisabled}
            >
              Exportar CSV
            </Button>
          </div>
        </form>
      </header>
    </section>
  );
}

export default SalesReportsFilters;
