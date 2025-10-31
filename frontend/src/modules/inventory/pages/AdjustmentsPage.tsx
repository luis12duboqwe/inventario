import { useMemo, useState } from "react";
import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import {
  AdjFiltersBar,
  AdjSummaryCards,
  AdjTable,
  AdjSidePanel,
  CreateAdjustmentModal,
} from "../components/adjustments";
import type { AdjustmentFilters, AdjustmentLineDraft, AdjustmentRow } from "../components/adjustments";

function AdjustmentsPage() {
  const [filters, setFilters] = useState<AdjustmentFilters>({});
  const [rows] = useState<AdjustmentRow[]>([]); // TODO(wire)
  const [loading] = useState<boolean>(false); // TODO(wire)
  const [selected, setSelected] = useState<AdjustmentRow | null>(null);
  const [showModal, setShowModal] = useState(false);

  const summaryItems = useMemo(
    () => [
      { label: "Ajustes hoy", value: "—" },
      { label: "Mes", value: "—" },
      { label: "Δ total", value: "—" },
      { label: "Daños", value: "—" },
    ],
    []
  );

  const handleSubmit = (payload: { warehouse: string; reason: string; note: string; lines: AdjustmentLineDraft[] }) => {
    void payload;
    // TODO(wire): enviar a servicio de ajustes y refrescar tabla
    setShowModal(false);
  };

  return (
    <div className="inventory-page">
      <PageHeader
        title="Ajustes de inventario"
        subtitle="Controla sobrantes, faltantes y correcciones de stock."
        actions={[
          {
            label: "Nuevo ajuste",
            onClick: () => setShowModal(true),
            variant: "primary",
          },
        ]}
      />

      <AdjSummaryCards items={summaryItems} />

      <PageToolbar>
        <AdjFiltersBar value={filters} onChange={setFilters} onNew={() => setShowModal(true)} />
      </PageToolbar>

      <AdjTable rows={rows} loading={loading} onRowClick={setSelected} />

      <AdjSidePanel row={selected} onClose={() => setSelected(null)} />

      <CreateAdjustmentModal open={showModal} onClose={() => setShowModal(false)} onSubmit={handleSubmit} />
    </div>
  );
}

export default AdjustmentsPage;
