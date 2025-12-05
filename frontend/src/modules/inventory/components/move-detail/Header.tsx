import React from "react";
import MoveStatusBadge from "../moves-list/StatusBadge";
import { Button } from "../../../../../components/ui/Button";

type Props = {
  number?: string;
  status: string;
  type?: string;
  onPrint?: () => void;
  onExportPDF?: () => void;
  onApprove?: () => void;
  onCancel?: () => void;
};

export default function Header({
  number,
  status,
  type,
  onPrint,
  onExportPDF,
  onApprove,
  onCancel,
}: Props) {
  return (
    <div className="flex justify-between items-center">
      <div>
        <div className="text-xs text-muted-foreground">Movimiento {type || ""}</div>
        <h2 className="m-0 mt-1 text-2xl font-bold">{number || "—"}</h2>
        <div className="mt-1.5">
          <MoveStatusBadge value={status} />
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={onPrint}>
          Imprimir
        </Button>
        <Button variant="ghost" onClick={onExportPDF}>
          PDF
        </Button>
        <Button
          variant="primary"
          onClick={onApprove}
          className="bg-green-600 hover:bg-green-700 text-white border-none font-bold"
        >
          Aprobar
        </Button>
        <Button variant="danger" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
