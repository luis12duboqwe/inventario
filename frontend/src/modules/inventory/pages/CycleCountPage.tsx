import { useMemo, useState } from "react";
import PageHeader from "../../../components/layout/PageHeader";
import PageToolbar from "../../../components/layout/PageToolbar";
import {
  PlanBar,
  StartCountModal,
  ScanIMEI,
  ItemsTable,
  DiscrepanciesTable,
  ReconcileModal,
} from "../components/cycle-count";
import type {
  CyclePlan,
  CycleCountRow,
  DiscrepancyRow,
} from "../components/cycle-count";

function CycleCountPage() {
  const [plan, setPlan] = useState<CyclePlan>({});
  const [rows, setRows] = useState<CycleCountRow[]>([]); // TODO(wire)
  const [diffs, setDiffs] = useState<DiscrepancyRow[]>([]);
  const [showStart, setShowStart] = useState(false);
  const [showReconcile, setShowReconcile] = useState(false);
  const [scanned, setScanned] = useState<string[]>([]);

  const summary = useMemo(
    () => ({
      total: rows.length,
      discrepancies: diffs.length,
    }),
    [rows.length, diffs.length]
  );

  const recalcDiffs = (nextRows: CycleCountRow[]) => {
    const nextDiffs = nextRows
      .map((row) => {
        const base = {
          id: row.id,
          name: row.name,
          expected: row.expected,
          counted: row.counted,
          delta: row.counted - row.expected,
        } satisfies Omit<DiscrepancyRow, "sku">;

        return row.sku ? { ...base, sku: row.sku } : base;
      })
      .filter((item) => item.delta !== 0);
    setDiffs(nextDiffs);
  };

  const handleChangeCount = (id: string, value: number) => {
    setRows((state) => {
      const next = state.map((row) => (row.id === id ? { ...row, counted: Math.max(0, value) } : row));
      recalcDiffs(next);
      return next;
    });
  };

  const handleScan = (imei: string) => {
    setScanned((state) => {
      if (state.includes(imei)) {
        return state;
      }
      // TODO(wire): registrar lectura en backend
      return [...state, imei];
    });
  };

  const handleStart = (payload: { plan: CyclePlan; responsible: string; note: string }) => {
    void payload;
    // TODO(wire): iniciar sesión de conteo
    setShowStart(false);
  };

  const handleReconcile = (payload: { note: string }) => {
    void payload;
    // TODO(wire): conciliar diferencias
    setShowReconcile(false);
  };

  return (
    <div className="inventory-page">
      <PageHeader
        title="Conteo cíclico"
        subtitle="Captura seriales y concilia diferencias en inventario."
        actions={[
          {
            label: "Iniciar conteo",
            onClick: () => setShowStart(true),
            variant: "primary",
          },
        ]}
      />

      <PageToolbar>
        <PlanBar value={plan} onChange={setPlan} onStart={() => setShowStart(true)} />
      </PageToolbar>

      <div className="card">
        <header className="card-header">
          <h3>Escaneo rápido</h3>
          <p className="card-subtitle">IMEIs únicos: {scanned.length}</p>
        </header>
        <ScanIMEI onAdd={handleScan} />
      </div>

      <ItemsTable rows={rows} onChangeCount={handleChangeCount} />

      <DiscrepanciesTable rows={diffs} />

      <div className="actions-bar actions-bar--end">
        <button type="button" className="ghost" onClick={() => setShowReconcile(true)} disabled={diffs.length === 0}>
          Conciliar diferencias
        </button>
      </div>

      <StartCountModal open={showStart} plan={plan} onClose={() => setShowStart(false)} onSubmit={handleStart} />

      <ReconcileModal open={showReconcile} diffs={diffs} onClose={() => setShowReconcile(false)} onSubmit={handleReconcile} />

      <section className="card">
        <header className="card-header">
          <h3>Resumen</h3>
        </header>
        <ul className="summary-list">
          <li>Total SKUs: {summary.total}</li>
          <li>Diferencias: {summary.discrepancies}</li>
        </ul>
      </section>
    </div>
  );
}

export default CycleCountPage;
