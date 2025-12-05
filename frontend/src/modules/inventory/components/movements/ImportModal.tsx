import React from "react";
import { Modal } from "../../../../../components/ui/Modal";
import { Button } from "../../../../../components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ImportModal({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <Modal
      isOpen={open}
      onClose={onClose}
      title="Importar movimientos"
      footer={
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose}>
            Cerrar
          </Button>
          <Button variant="primary">Procesar</Button>
        </div>
      }
    >
      <div className="p-4">{/* Content would go here */}</div>
    </Modal>
  );
}
