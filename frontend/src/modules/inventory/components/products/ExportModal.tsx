import React from "react";
import { Modal } from "@components/ui/Modal";
import { Button } from "@components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ExportModal({ open, onClose }: Props) {
  return (
    <Modal
      isOpen={!!open}
      onClose={onClose}
      title="Exportar productos"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
          <Button variant="primary">Exportar</Button>
        </>
      }
    >
      <div className="text-muted-foreground">
        {/* Opciones de exportación (CSV/XLSX) */}
        Opciones de exportación próximamente.
      </div>
    </Modal>
  );
}
