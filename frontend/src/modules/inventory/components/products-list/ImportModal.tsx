import React from "react";
import Modal from "@components/ui/Modal";
import Button from "@components/ui/Button";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ImportModal({ open = false, onClose = () => {} }: Props) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Importar productos"
      description="Sube un archivo CSV o XLSX para actualizar el inventario."
      size="sm"
      footer={
        <>
          <Button onClick={onClose} variant="ghost">
            Cancelar
          </Button>
          <Button variant="primary">Subir</Button>
        </>
      }
    >
      <div className="ui-field">
        <label className="ui-field__label">Archivo</label>
        <div className="ui-field__control">
          <input type="file" accept=".csv,.xlsx" className="ui-field__input" />
        </div>
      </div>
    </Modal>
  );
}
