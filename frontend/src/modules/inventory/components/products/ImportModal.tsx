import React from "react";
import { Modal } from "@components/ui/Modal";
import { Button } from "@components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ImportModal({ open, onClose }: Props) {
  return (
    <Modal
      isOpen={!!open}
      onClose={onClose}
      title="Importar productos"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
          <Button variant="primary">Procesar</Button>
        </>
      }
    >
      <div className="text-muted-foreground">
        {/* Dropzone y validador (se conectará en pack posterior) */}
        Funcionalidad de importación próximamente.
      </div>
    </Modal>
  );
}
