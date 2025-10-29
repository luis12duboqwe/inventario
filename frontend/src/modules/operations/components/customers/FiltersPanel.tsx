import type { CustomerFilters } from "../../../../types/customers";

type Option = { value: string; label: string };

type CustomersFiltersPanelProps = {
  filters: CustomerFilters;
  statuses: Option[];
  types: Option[];
  debtOptions: Option[];
  customersCount: number;
  totalDebt: number;
  onFilterChange: <Field extends keyof CustomerFilters>(
    field: Field,
    value: CustomerFilters[Field],
  ) => void;
  formatCurrency: (value: number) => string;
};

const CustomersFiltersPanel = ({
  filters,
  statuses,
  types,
  debtOptions,
  customersCount,
  totalDebt,
  onFilterChange,
  formatCurrency,
}: CustomersFiltersPanelProps) => {
  return (
    <div className="form-grid">
      <label className="span-2">
        Búsqueda rápida
        <input
          value={filters.search}
          onChange={(event) => onFilterChange("search", event.target.value)}
          placeholder="Nombre, correo, contacto o nota"
        />
        <span className="muted-text">
          Se actualiza automáticamente al escribir (mínimo 2 caracteres).
        </span>
      </label>
      <label>
        Estado
        <select
          value={filters.status}
          onChange={(event) => onFilterChange("status", event.target.value)}
        >
          <option value="todos">Todos</option>
          {statuses.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Tipo
        <select
          value={filters.customerType}
          onChange={(event) => onFilterChange("customerType", event.target.value)}
        >
          <option value="todos">Todos</option>
          {types.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Saldo pendiente
        <select
          value={filters.debt}
          onChange={(event) => onFilterChange("debt", event.target.value)}
        >
          {debtOptions.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <div>
        <span className="muted-text">Clientes encontrados</span>
        <strong>{customersCount}</strong>
      </div>
      <div>
        <span className="muted-text">Deuda consolidada</span>
        <strong>${formatCurrency(totalDebt)}</strong>
      </div>
    </div>
  );
};

export default CustomersFiltersPanel;
