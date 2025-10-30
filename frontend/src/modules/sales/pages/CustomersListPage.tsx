import React, { useState } from "react";
import { CustomersFiltersBar, CustomersTable } from "../components/customers";

type CustomerRow = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  tier?: string;
  lastSale?: string;
};

export function CustomersListPage() {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [rows] = useState<CustomerRow[]>([]); // TODO(wire)

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <CustomersFiltersBar value={filters} onChange={setFilters} />
      <CustomersTable
        rows={rows}
        onRowClick={() => {
          // TODO(nav)
        }}
      />
    </div>
  );
}
