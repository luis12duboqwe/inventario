import type { ChangeEvent } from "react";

export type AdjustmentFilters = {
  query?: string;
  reason?: string | "ALL";
  dateFrom?: string;
  dateTo?: string;
  user?: string;
};

type Props = {
  value: AdjustmentFilters;
  onChange: (value: AdjustmentFilters) => void;
  onNew?: () => void;
};

const reasonOptions: Array<{ value: AdjustmentFilters["reason"]; label: string }> = [
  { value: "ALL", label: "Motivo" },
  { value: "DAMAGE", label: "Daño" },
  { value: "THEFT", label: "Robo" },
  { value: "WRITE_OFF", label: "Baja" },
  { value: "INITIAL_BALANCE", label: "Inventario inicial" },
  { value: "CORRECTION", label: "Corrección" },
  { value: "LOST_FOUND", label: "Hallazgo" },
];

function FiltersBar({ value, onChange, onNew }: Props) {
  const handleChange = (field: keyof AdjustmentFilters) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    onChange({
      ...value,
      [field]: event.target.value,
    });
  };

  return (
    <div className="inventory-filters-grid">
      <input
        placeholder="SKU o producto"
        value={value.query ?? ""}
        onChange={handleChange("query")}
      />
      <select value={value.reason ?? "ALL"} onChange={handleChange("reason")}>
        {reasonOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <input placeholder="Usuario" value={value.user ?? ""} onChange={handleChange("user")} />
      <input type="date" value={value.dateFrom ?? ""} onChange={handleChange("dateFrom")} />
      <input type="date" value={value.dateTo ?? ""} onChange={handleChange("dateTo")} />
      <button type="button" className="primary" onClick={onNew}>
        Nuevo ajuste
      </button>
    </div>
  );
}

export default FiltersBar;
