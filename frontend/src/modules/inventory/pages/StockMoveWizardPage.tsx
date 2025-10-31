import React from "react";
import {
  MoveStepItems,
  MoveStepReview,
  MoveStepSelectType,
  MoveStepSourceDest,
  MoveStepSuccess,
  MoveStepper,
} from "../components/move-wizard";

type MoveType = "IN" | "OUT" | "TRANSFER" | "ADJUST";
type WizardItem = { id: string; sku: string; name: string; qty: number };
type WizardState = {
  sourceId: string;
  destId: string;
  reason: string;
  items: WizardItem[];
};

type CreatedMove = { id: string; number?: string };

const steps = ["Tipo", "Origen/Destino", "Items", "Revisión", "Hecho"] as const;

export default function StockMoveWizardPage() {
  const [active, setActive] = React.useState(0);
  const [type, setType] = React.useState<MoveType>("IN");
  const [form, setForm] = React.useState<WizardState>({ sourceId: "", destId: "", reason: "", items: [] });
  const [created, setCreated] = React.useState<CreatedMove | null>(null);

  const handleAddItem = React.useCallback(() => {
    setForm((prev) => ({
      ...prev,
      items: [
        ...prev.items,
        { id: String(Date.now()), sku: "SKU", name: "Producto", qty: 1 },
      ],
    }));
  }, []);

  const handleEditItem = React.useCallback((id: string, patch: Partial<WizardItem>) => {
    setForm((prev) => ({
      ...prev,
      items: prev.items.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  }, []);

  const handleRemoveItem = React.useCallback((id: string) => {
    setForm((prev) => ({
      ...prev,
      items: prev.items.filter((item) => item.id !== id),
    }));
  }, []);

  const handleCreate = React.useCallback(() => {
    setCreated({ id: "temp-id", number: `MV-${Date.now()}` });
    setActive(4);
  }, []);

  const openDetail = React.useCallback((id?: string) => {
    // TODO: conectar con navegación al detalle real
    if (id) {
      console.info(`Abrir detalle de movimiento ${id}`);
    }
  }, []);

  const next = React.useCallback(() => {
    setActive((value) => Math.min(value + 1, steps.length - 1));
  }, []);

  const back = React.useCallback(() => {
    setActive((value) => Math.max(value - 1, 0));
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <MoveStepper steps={[...steps]} active={active} />
      {active === 0 && <MoveStepSelectType value={type} onChange={setType} />}
      {active === 1 && (
        <MoveStepSourceDest
          type={type}
          sourceId={form.sourceId}
          destId={form.destId}
          reason={form.reason}
          onChange={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
        />
      )}
      {active === 2 && (
        <MoveStepItems
          items={form.items}
          onAdd={handleAddItem}
          onEdit={handleEditItem}
          onRemove={handleRemoveItem}
        />
      )}
      {active === 3 && (
        <MoveStepReview summary={{ type, ...form }} onSubmit={handleCreate} />
      )}
      {active === 4 && (
        <MoveStepSuccess number={created?.number} onOpen={() => openDetail(created?.id)} />
      )}
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button
          onClick={back}
          disabled={active === 0}
          style={{ padding: "8px 12px", borderRadius: 8 }}
          type="button"
        >
          Atrás
        </button>
        <button
          onClick={next}
          disabled={active >= steps.length - 2}
          style={{ padding: "8px 12px", borderRadius: 8 }}
          type="button"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
