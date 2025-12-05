import React from "react";
import { Button } from "../../../../../components/ui/Button";
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
    <div className="flex justify-between items-center">
      <div>
        <div className="text-xs text-muted-foreground">Producto</div>
        <h2 className="m-0 mt-1 text-2xl font-bold">{name || "—"}</h2>
        <div className="flex gap-2 items-center mt-1">
          <span className="text-xs text-muted-foreground">{sku || "—"}</span>
          <ProductStatusBadge value={status} />
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={onPrint}>
          Imprimir
        </Button>
        <Button variant="ghost" onClick={onExportPDF}>
          PDF
        </Button>
      </div>
    </div>
  );
}
