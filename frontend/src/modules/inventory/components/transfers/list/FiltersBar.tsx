import type { ChangeEvent } from "react";

type Filters = {
  query?: string;
  status?: string | "ALL";
  from?: string;
  to?: string;
  dateFrom?: string;
  dateTo?: string;
};

type Props = {
  value: Filters;
  onChange: (value: Filters) => void;
  onNew?: () => void;
};

const statusOptions: Array<{ value: Filters["status"]; label: string }> = [
  { value: "ALL", label: "Estado" },
  { value: "SOLICITADA", label: "Solicitada" },
  { value: "EN_TRANSITO", label: "En tránsito" },
  { value: "RECIBIDA", label: "Recibida" },
  { value: "CANCELADA", label: "Cancelada" },
];

function FiltersBar({ value, onChange, onNew }: Props) {
  const handleChange = (field: keyof Filters) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    onChange({
      ...value,
      [field]: event.target.value,
    });
  };

  return (
    <div className="inventory-filters-grid">
      <input placeholder="#TRF o producto" value={value.query ?? ""} onChange={handleChange("query")} />
      <select value={value.status ?? "ALL"} onChange={handleChange("status")}>
        {statusOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <input placeholder="Origen" value={value.from ?? ""} onChange={handleChange("from")} />
      <input placeholder="Destino" value={value.to ?? ""} onChange={handleChange("to")} />
      <input type="date" value={value.dateFrom ?? ""} onChange={handleChange("dateFrom")} />
      <input type="date" value={value.dateTo ?? ""} onChange={handleChange("dateTo")} />
      <button type="button" className="primary" onClick={onNew}>
        Nueva transferencia
      </button>
    </div>
  );
}

export type { Filters as TransferFilters };
export default FiltersBar;
