import type { UserQueryFilters, Store } from "../../../../api";
import { FILTER_ALL_VALUE, FILTER_ALL_LABEL } from "../../../../constants/filters";

export type FiltersPanelProps = {
  search: string;
  onSearchChange: (value: string) => void;
  roleFilter: string;
  onRoleFilterChange: (value: string) => void;
  statusFilter: UserQueryFilters["status"];
  onStatusFilterChange: (value: UserQueryFilters["status"]) => void;
  storeFilter: number | typeof FILTER_ALL_VALUE;
  onStoreFilterChange: (value: number | typeof FILTER_ALL_VALUE) => void;
  roleOptions: string[];
  stores: Store[];
};

function FiltersPanel({
  search,
  onSearchChange,
  roleFilter,
  onRoleFilterChange,
  statusFilter,
  onStatusFilterChange,
  storeFilter,
  onStoreFilterChange,
  roleOptions,
  stores,
}: FiltersPanelProps) {
  return (
    <div className="user-filters">
      <label>
        <span>Búsqueda</span>
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Correo o nombre completo"
        />
      </label>
      <label>
        <span>Rol</span>
        <select value={roleFilter} onChange={(event) => onRoleFilterChange(event.target.value)}>
          <option value={FILTER_ALL_VALUE}>{FILTER_ALL_LABEL}</option>
          {roleOptions.map((role) => (
            <option key={role} value={role}>
              {role}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Estado</span>
        <select
          value={statusFilter}
          onChange={(event) =>
            onStatusFilterChange(event.target.value as UserQueryFilters["status"])
          }
        >
          <option value={FILTER_ALL_VALUE}>{FILTER_ALL_LABEL}</option>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
          <option value="locked">Bloqueados</option>
        </select>
      </label>
      <label>
        <span>Sucursal</span>
        <select
          value={storeFilter === FILTER_ALL_VALUE ? FILTER_ALL_VALUE : String(storeFilter)}
          onChange={(event) =>
            onStoreFilterChange(
              event.target.value === FILTER_ALL_VALUE
                ? FILTER_ALL_VALUE
                : Number(event.target.value),
            )
          }
        >
          <option value={FILTER_ALL_VALUE}>Todas</option>
          {stores.map((store) => (
            <option key={store.id} value={store.id}>
              {store.name}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export default FiltersPanel;
