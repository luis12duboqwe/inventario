import React from "react";

type Props = {
  title: string;
  rows: [string, string | number][];
  onClose?: () => void;
};

export default function SidePanel({ title, rows, onClose }: Props) {
  return (
    <aside className="sales-side-panel">
      <div className="sales-side-panel-header">
        <h3 className="sales-side-panel-title">{title}</h3>
        <button onClick={onClose} className="sales-side-panel-close">
          Cerrar
        </button>
      </div>
      <div className="sales-side-panel-content">
        {(rows ?? []).map(([label, value], index) => (
          <div key={index} className="sales-side-panel-row">
            <span className="sales-side-panel-label">{label}</span>
            <span>{String(value)}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
