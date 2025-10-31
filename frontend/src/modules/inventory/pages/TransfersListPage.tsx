import { useMemo, useState } from "react";
import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import {
  TransfersFiltersBar,
  TransfersSummaryCards,
  TransfersTable,
  TransfersSidePanel,
} from "../components/transfers/list";
import type { TransferFilters, TransferRow } from "../components/transfers/list";

function TransfersListPage() {
  const [filters, setFilters] = useState<TransferFilters>({});
  const [rows] = useState<TransferRow[]>([]); // TODO(wire)
  const [loading] = useState(false); // TODO(wire)
  const [selected, setSelected] = useState<TransferRow | null>(null);

  const summaryItems = useMemo(
    () => [
      { label: "Solicitado", value: "—" },
      { label: "En tránsito", value: "—" },
      { label: "Recibido", value: "—" },
      { label: "Cancelado", value: "—" },
    ],
    []
  );

  return (
    <div className="inventory-page">
      <PageHeader
        title="Transferencias"
        subtitle="Gestión de envíos entre sucursales y almacenes."
        actions={[
          {
            label: "Nueva transferencia",
            onClick: () => {
              // TODO(wire): abrir flujo de creación de transferencia
            },
            variant: "primary",
          },
        ]}
      />

      <TransfersSummaryCards items={summaryItems} />

      <PageToolbar>
        <TransfersFiltersBar
          value={filters}
          onChange={setFilters}
          onNew={() => {
            // TODO(wire): abrir flujo de creación de transferencia
          }}
        />
      </PageToolbar>

      <TransfersTable rows={rows} loading={loading} onRowClick={setSelected} />

      <TransfersSidePanel row={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

export default TransfersListPage;
