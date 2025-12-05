import React from "react";
import { Modal } from "@components/ui/Modal";
import { Button } from "@components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onConfirm?: () => void;
};

export default function CancelModal({ open, onClose, onConfirm }: Props) {
  return (
    <Modal
      isOpen={!!open}
      onClose={onClose}
      title="Cancelar movimientos"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            No
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            Sí, cancelar
          </Button>
        </>
      }
    >
      <p className="text-muted-foreground">
        ¿Seguro que deseas cancelar los movimientos seleccionados?
      </p>
    </Modal>
  );
}
