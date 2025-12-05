import React from "react";
import { Modal } from "@components/ui/Modal";
import { Button } from "@components/ui/Button";
import { TextField } from "@components/ui/TextField";

type Props = {
  open?: boolean;
  onClose?: () => void;
};

export default function ImportModal({ open, onClose }: Props) {
  return (
    <Modal
      isOpen={!!open}
      onClose={onClose}
      title="Importar movimientos (CSV/XLSX)"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" type="button">
            Subir
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <TextField type="file" accept=".csv,.xlsx" fullWidth />
      </div>
    </Modal>
  );
}
