import type { ReactNode } from "react";
import type { AdjustmentRow } from "./Table";

type DetailedRow = AdjustmentRow & {
  note?: string;
  attachments?: Array<{ id: string; name: string; url?: string }>;
};

type Props = {
  row?: DetailedRow | null;
  onClose?: () => void;
  footer?: ReactNode;
};

function SidePanel({ row, onClose, footer }: Props) {
  if (!row) {
    return null;
  }

  const fields: Array<[string, ReactNode]> = [
    ["Fecha", new Date(row.date).toLocaleString()],
    ["#AJ", row.number ?? "—"],
    ["Almacén", row.warehouse ?? "—"],
    ["Ítems", row.items],
    ["Δ Cantidad", Intl.NumberFormat().format(row.delta)],
    ["Motivo", row.reason],
    ["Usuario", row.user ?? "—"],
    ["Notas", row.note ?? "—"],
  ];

  return (
    <aside className="inventory-side-panel" aria-label="Detalle de ajuste">
      <header className="inventory-side-panel__header">
        <h3>Ajuste #{row.number ?? row.id}</h3>
        <button type="button" onClick={onClose} className="ghost">
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

      {Array.isArray(row.attachments) && row.attachments.length > 0 ? (
        <section className="inventory-side-panel__section">
          <h4>Adjuntos</h4>
          <ul>
            {row.attachments.map((file) => (
              <li key={file.id}>
                {file.url ? (
                  <a href={file.url} target="_blank" rel="noreferrer">
                    {file.name}
                  </a>
                ) : (
                  <span>{file.name}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {footer ? <footer className="inventory-side-panel__footer">{footer}</footer> : null}
    </aside>
  );
}

export default SidePanel;
