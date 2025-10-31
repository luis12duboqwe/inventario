import { useState } from "react";
import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import { LedgerFilters, LedgerTable } from "../components/ledger";
import type { LedgerFiltersValue, LedgerRow } from "../components/ledger";

function StockLedgerPage() {
  const [filters, setFilters] = useState<LedgerFiltersValue>({});
  const [rows] = useState<LedgerRow[]>([]); // TODO(wire)

  return (
    <div className="inventory-page">
      <PageHeader
        title="Kardex / Stock Ledger"
        subtitle="Consulta detallada de movimientos por producto y almacén."
      />

      <PageToolbar>
        <LedgerFilters value={filters} onChange={setFilters} />
      </PageToolbar>

      <LedgerTable rows={rows} />
    </div>
  );
}

export default StockLedgerPage;
