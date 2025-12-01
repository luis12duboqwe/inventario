import { useMemo, useState } from "react";
import type { Store } from "../../../api";

import { useDashboard } from "../../dashboard/context/DashboardContext";

type MovementType = "RECEPCION" | "AJUSTE" | "CONTEO";

type MovementDraft = {
  storeId: number | "general";
  movementType: MovementType;
  reference: string;
  reason: string;
};

type MovementRecord = MovementDraft & {
  id: string;
  createdAt: Date;
};

type Props = {
  stores: Store[];
  defaultStoreId?: number | null;
};

const MOVEMENT_TYPES: Array<{ id: MovementType; label: string }> = [
  { id: "RECEPCION", label: "Recepción de inventario" },
  { id: "AJUSTE", label: "Ajuste interno" },
  { id: "CONTEO", label: "Conteo cíclico" },
];

const createInitialDraft = (defaultStoreId?: number | null): MovementDraft => ({
  storeId: defaultStoreId ?? "general",
  movementType: "AJUSTE",
  reference: "",
  reason: "",
});

function InternalMovementsPanel({ stores, defaultStoreId = null }: Props) {
  const { pushToast } = useDashboard();
  const [draft, setDraft] = useState<MovementDraft>(() => createInitialDraft(defaultStoreId));
  const [records, setRecords] = useState<MovementRecord[]>([]);

  const handleChange = <K extends keyof MovementDraft>(field: K, value: MovementDraft[K]) => {
    setDraft((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    if (!draft.reason.trim()) {
      pushToast({ message: "Indica un motivo corporativo para el movimiento interno.", variant: "warning" });
      return;
    }
    const id = crypto.randomUUID();
    const entry: MovementRecord = {
      ...draft,
      reason: draft.reason.trim(),
      reference: draft.reference.trim(),
      id,
      createdAt: new Date(),
    };
    setRecords((current) => [entry, ...current].slice(0, 15));
    setDraft(createInitialDraft(defaultStoreId));
    pushToast({ message: "Movimiento interno registrado localmente", variant: "success" });
  };

  const storeLookup = useMemo(() => {
    const map = new Map<number, string>();
    stores.forEach((store) => map.set(store.id, store.name));
    return map;
  }, [stores]);

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Movimientos internos</h2>
          <p className="card-subtitle">Captura recepciones, ajustes y conteos rápidos.</p>
        </div>
      </header>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          <span>Sucursal destino</span>
          <select
            value={draft.storeId === "general" ? "general" : String(draft.storeId)}
            onChange={(event) => {
              const value = event.target.value;
              handleChange("storeId", value === "general" ? "general" : Number(value));
            }}
          >
            <option value="general">Todas</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Tipo de movimiento</span>
          <select
            value={draft.movementType}
            onChange={(event) => handleChange("movementType", event.target.value as MovementType)}
          >
            {MOVEMENT_TYPES.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Referencia interna</span>
          <input
            type="text"
            value={draft.reference}
            onChange={(event) => handleChange("reference", event.target.value)}
            placeholder="Ticket, folio o sesión"
          />
        </label>
        <label className="wide">
          <span>Motivo corporativo</span>
          <textarea
            required
            minLength={5}
            value={draft.reason}
            onChange={(event) => handleChange("reason", event.target.value)}
            placeholder="Describe el motivo del movimiento"
          />
        </label>
        <div className="form-actions">
          <button type="submit" className="btn btn--primary">
            Registrar
          </button>
        </div>
      </form>
      <div className="section-divider">
        <h3>Bitácora interna reciente</h3>
        {records.length === 0 ? (
          <p className="muted-text">Aún no se registran movimientos durante esta sesión.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Sucursal</th>
                  <th scope="col">Tipo</th>
                  <th scope="col">Referencia</th>
                  <th scope="col">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td data-label="Fecha">{record.createdAt.toLocaleString("es-HN")}</td>
                    <td data-label="Sucursal">
                      {record.storeId === "general" ? "Todas" : storeLookup.get(record.storeId) ?? "Desconocida"}
                    </td>
                    <td data-label="Tipo">{MOVEMENT_TYPES.find((option) => option.id === record.movementType)?.label}</td>
                    <td data-label="Referencia">{record.reference || "—"}</td>
                    <td data-label="Motivo">{record.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default InternalMovementsPanel;
