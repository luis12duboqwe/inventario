import React from "react";

import ProductStatusBadge from "../products-list/StatusBadge";

type Props = {
  name?: string;
  sku?: string;
  status?: "ACTIVE" | "INACTIVE" | string;
  onPrint?: () => void;
  onExportPDF?: () => void;
};

export default function Header({ name, sku, status = "ACTIVE", onPrint, onExportPDF }: Props) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Producto</div>
        <h2 style={{ margin: "4px 0 0 0" }}>{name || "—"}</h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 12, color: "#94a3b8" }}>{sku || "—"}</span>
          <ProductStatusBadge value={status} />
        </div>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onPrint} style={{ padding: "8px 12px", borderRadius: 8 }}>
          Imprimir
        </button>
        <button onClick={onExportPDF} style={{ padding: "8px 12px", borderRadius: 8 }}>
          PDF
        </button>
      </div>
    </div>
  );
}
