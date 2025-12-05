import React from "react";
import { Modal } from "@components/ui/Modal";
import { Button } from "@components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
  onConfirm?: () => void;
};

export default function ApproveModal({ open, onClose, onConfirm }: Props) {
  return (
    <Modal
      isOpen={!!open}
      onClose={onClose}
      title="Aprobar movimientos"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            No
          </Button>
          <Button variant="success" onClick={onConfirm}>
            Sí, aprobar
          </Button>
        </>
      }
    >
      <p className="text-muted-foreground">¿Confirmas aprobar los movimientos seleccionados?</p>
    </Modal>
  );
}
