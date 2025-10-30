import type { ReactNode } from "react";
import type { TransferRow } from "./Table";

type TransferDetail = TransferRow & {
  createdBy?: string;
  updatedAt?: string;
  notes?: string;
  progress?: ReactNode;
};

type Props = {
  row?: TransferDetail | null;
  onClose?: () => void;
};

function SidePanel({ row, onClose }: Props) {
  if (!row) {
    return null;
  }

  const fields: Array<[string, ReactNode]> = [
    ["Fecha", new Date(row.date).toLocaleString()],
    ["#TRF", row.number ?? "—"],
    ["Origen", row.from ?? "—"],
    ["Destino", row.to ?? "—"],
    ["Estado", row.status],
    ["Ítems", row.items],
    ["Creado por", row.createdBy ?? "—"],
    ["Actualizado", row.updatedAt ? new Date(row.updatedAt).toLocaleString() : "—"],
    ["Notas", row.notes ?? "—"],
  ];

  return (
    <aside className="inventory-side-panel" aria-label="Detalle de transferencia">
      <header className="inventory-side-panel__header">
        <h3>Transferencia #{row.number ?? row.id}</h3>
        <button type="button" className="ghost" onClick={onClose}>
          Cerrar
        </button>
      </header>
      <dl className="inventory-side-panel__list">
        {fields.map(([label, value]) => (
          <div key={label} className="inventory-side-panel__item">
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {row.progress ? <div className="inventory-side-panel__section">{row.progress}</div> : null}
    </aside>
  );
}

export default SidePanel;
