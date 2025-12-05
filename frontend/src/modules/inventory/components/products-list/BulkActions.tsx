import React from "react";
import Button from "@components/ui/Button";

type Props = {
  selectedCount: number;
  onActivate?: () => void;
  onDeactivate?: () => void;
  onExport?: () => void;
  onImport?: () => void;
  onMoveCategory?: () => void;
  onTag?: () => void;
  onLabel?: () => void;
  canGenerateLabel?: boolean;
};

export default function BulkActions({
  selectedCount,
  onActivate,
  onDeactivate,
  onExport,
  onImport,
  onMoveCategory,
  onTag,
  onLabel,
  canGenerateLabel = false,
}: Props) {
  if (selectedCount <= 0) {
    return null;
  }

  return (
    <div className="flex items-center justify-between flex-wrap gap-4">
      <div className="text-muted-foreground text-sm">{selectedCount} seleccionados</div>
      <div className="flex gap-2 flex-wrap">
        <Button onClick={onActivate} variant="success" size="sm">
          Activar
        </Button>
        <Button onClick={onDeactivate} variant="secondary" size="sm">
          Desactivar
        </Button>
        {onLabel ? (
          <Button
            onClick={onLabel}
            disabled={!canGenerateLabel}
            variant="primary"
            size="sm"
            title={
              canGenerateLabel
                ? "Generar etiqueta PDF"
                : "Selecciona un solo producto y una sucursal para generar la etiqueta"
            }
          >
            Etiqueta PDF
          </Button>
        ) : null}
        <Button onClick={onTag} variant="secondary" size="sm">
          Etiquetar
        </Button>
        <Button onClick={onMoveCategory} variant="secondary" size="sm">
          Mover categoría
        </Button>
        <Button onClick={onImport} variant="secondary" size="sm">
          Importar
        </Button>
        <Button onClick={onExport} variant="ghost" size="sm">
          Exportar
        </Button>
      </div>
    </div>
  );
}
