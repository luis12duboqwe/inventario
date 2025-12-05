import React from "react";
import { Button } from "../../../../../components/ui/Button";

type Props = {
  selectedCount: number;
  onExport?: () => void;
  onDelete?: () => void;
};

export default function BulkActions({ selectedCount, onExport, onDelete }: Props) {
  if (selectedCount <= 0) return null;
  return (
    <div className="flex gap-2 items-center justify-between">
      <div className="text-muted-foreground text-sm">{selectedCount} seleccionados</div>
      <div className="flex gap-2">
        <Button variant="ghost" onClick={onExport}>
          Exportar
        </Button>
        <Button variant="danger" onClick={onDelete}>
          Eliminar
        </Button>
      </div>
    </div>
  );
}
