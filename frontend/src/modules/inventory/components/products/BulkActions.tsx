import React from "react";
import { Button } from "@components/ui/Button";

type Props = {
  selectedCount: number;
  onExport?: () => void;
  onAdjustStock?: () => void;
  onDelete?: () => void;
};

export default function BulkActions({ selectedCount, onExport, onAdjustStock, onDelete }: Props) {
  if (selectedCount <= 0) return null;
  return (
    <div className="flex items-center justify-between p-4 bg-surface rounded-lg border border-border mb-4">
      <div className="text-sm text-muted-foreground">{selectedCount} seleccionados</div>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={onExport}>
          Exportar
        </Button>
        <Button variant="primary" onClick={onAdjustStock}>
          Ajustar stock
        </Button>
        <Button variant="danger" onClick={onDelete}>
          Eliminar
        </Button>
      </div>
    </div>
  );
}
