import type { FormEvent } from "react";
import type { PurchaseVendor } from "@api/purchases";
import type { UserAccount } from "@api/users";
import type { PurchaseRecordFilters } from "../../../../types/purchases";

type PurchasesFiltersPanelProps = {
  filtersDraft: PurchaseRecordFilters;
  vendors: PurchaseVendor[];
  users: UserAccount[];
  onFiltersChange: <Field extends keyof PurchaseRecordFilters>(
    field: Field,
    value: PurchaseRecordFilters[Field],
  ) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onReset: () => void;
  onExport: (format: "pdf" | "xlsx") => void;
};

const PurchasesFiltersPanel = ({
  filtersDraft,
  vendors,
  users,
  onFiltersChange,
  onSubmit,
  onReset,
  onExport,
}: PurchasesFiltersPanelProps) => {
  return (
    <>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Proveedor
          <select
            value={filtersDraft.vendorId}
            onChange={(event) => onFiltersChange("vendorId", event.target.value)}
          >
            <option value="">Todos</option>
            {vendors.map((vendor) => (
              <option key={vendor.id_proveedor} value={vendor.id_proveedor}>
                {vendor.nombre}
              </option>
            ))}
          </select>
        </label>
        <label>
          Usuario
          <select
            value={filtersDraft.userId}
            onChange={(event) => onFiltersChange("userId", event.target.value)}
          >
            <option value="">Todos</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name || user.username}
              </option>
            ))}
          </select>
        </label>
        <label>
          Desde
          <input
            type="date"
            value={filtersDraft.dateFrom}
            onChange={(event) => onFiltersChange("dateFrom", event.target.value)}
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            value={filtersDraft.dateTo}
            onChange={(event) => onFiltersChange("dateTo", event.target.value)}
          />
        </label>
        <label>
          Estado
          <input
            value={filtersDraft.status}
            onChange={(event) => onFiltersChange("status", event.target.value)}
            placeholder="Ej. REGISTRADA"
          />
        </label>
        <label>
          Búsqueda
          <input
            value={filtersDraft.search}
            onChange={(event) => onFiltersChange("search", event.target.value)}
            placeholder="Proveedor, referencia..."
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn btn--primary">
            Aplicar filtros
          </button>
          <button type="button" className="btn btn--ghost" onClick={onReset}>
            Limpiar
          </button>
        </div>
      </form>
      <div className="actions-row">
        <button type="button" className="btn btn--secondary" onClick={() => onExport("pdf")}>
          Exportar PDF
        </button>
        <button type="button" className="btn btn--secondary" onClick={() => onExport("xlsx")}>
          Exportar Excel
        </button>
      </div>
    </>
  );
};

export default PurchasesFiltersPanel;
