import type { ChangeEvent } from "react";

type Filters = {
  sku?: string;
  dateFrom?: string;
  dateTo?: string;
  warehouse?: string;
};

type Props = {
  value: Filters;
  onChange: (value: Filters) => void;
};

function LedgerFilters({ value, onChange }: Props) {
  const handleChange = (field: keyof Filters) => (event: ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...value,
      [field]: event.target.value,
    });
  };

  return (
    <div className="inventory-filters-grid">
      <input placeholder="SKU" value={value.sku ?? ""} onChange={handleChange("sku")} />
      <input placeholder="Almacén" value={value.warehouse ?? ""} onChange={handleChange("warehouse")} />
      <input type="date" value={value.dateFrom ?? ""} onChange={handleChange("dateFrom")} />
      <input type="date" value={value.dateTo ?? ""} onChange={handleChange("dateTo")} />
    </div>
  );
}

export type { Filters as LedgerFiltersValue };
export default LedgerFilters;
