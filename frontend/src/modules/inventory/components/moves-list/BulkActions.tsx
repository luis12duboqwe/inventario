import React from "react";
import { Button } from "@components/ui/Button";

type Props = {
  selectedCount: number;
  onApprove?: () => void;
  onCancel?: () => void;
  onExport?: () => void;
  onPrint?: () => void;
  onImport?: () => void;
};

export default function BulkActions({
  selectedCount,
  onApprove,
  onCancel,
  onExport,
  onPrint,
  onImport,
}: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div className="flex items-center justify-between p-4 bg-surface rounded-lg border border-border mb-4">
      <div className="text-sm text-muted-foreground">{selectedCount} seleccionados</div>
      <div className="flex gap-2 flex-wrap">
        <Button variant="success" onClick={onApprove}>
          Aprobar
        </Button>
        <Button variant="danger" onClick={onCancel}>
          Cancelar
        </Button>
        <Button variant="ghost" onClick={onImport}>
          Importar
        </Button>
        <Button variant="ghost" onClick={onExport}>
          Exportar
        </Button>
        <Button variant="ghost" onClick={onPrint}>
          Imprimir
        </Button>
      </div>
    </div>
  );
}
