import React from "react";
import Modal from "@components/ui/Modal";
import Button from "@components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ExportModal({ open = false, onClose = () => {} }: Props) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Exportar productos"
      size="sm"
      footer={
        <>
          <Button onClick={onClose} variant="ghost">
            Cerrar
          </Button>
          <Button variant="primary">Exportar</Button>
        </>
      }
    >
      <p>¿Desea exportar el catálogo de productos?</p>
    </Modal>
  );
}
