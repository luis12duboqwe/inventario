import type { RepairOrder } from "../../../api";

type FiltersPanelProps = {
  statusFilter: RepairOrder["status"] | "TODOS";
  statusOptions: Array<RepairOrder["status"] | "TODOS">;
  onStatusFilterChange: (value: RepairOrder["status"] | "TODOS") => void;
  search: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  totalOrders: number;
  getStatusLabel: (status: RepairOrder["status"]) => string;
  dateFrom: string;
  dateTo: string;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
};

function FiltersPanel({
  statusFilter,
  statusOptions,
  onStatusFilterChange,
  search,
  onSearchChange,
  searchPlaceholder = "Cliente, técnico, daño o folio",
  totalOrders,
  getStatusLabel,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
}: FiltersPanelProps) {
  return (
    <div className="repair-orders-toolbar">
      <div className="repair-orders-toolbar__filters">
        <label>
          Filtrar por estado
          <select
            value={statusFilter}
            onChange={(event) => onStatusFilterChange(event.target.value as RepairOrder["status"] | "TODOS")}
          >
            {statusOptions.map((option) =>
              option === "TODOS" ? (
                <option key="todos" value="TODOS">
                  Todos
                </option>
              ) : (
                <option key={option} value={option}>
                  {getStatusLabel(option)}
                </option>
              ),
            )}
          </select>
        </label>
        <label>
          Buscar
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={searchPlaceholder}
          />
        </label>
        <label>
          Desde
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => onDateFromChange(event.target.value)}
          />
        </label>
        <label>
          Hasta
          <input
            type="date"
            value={dateTo}
            onChange={(event) => onDateToChange(event.target.value)}
          />
        </label>
      </div>
      <div className="repair-orders-toolbar__meta">
        <span className="muted-text">Órdenes registradas</span>
        <strong>{totalOrders}</strong>
      </div>
    </div>
  );
}

export type { FiltersPanelProps };
export default FiltersPanel;
