import React from "react";
import { Modal } from "@components/ui/Modal";
import { Button } from "@components/ui/Button";
import { TextField } from "@components/ui/TextField";
import type { ProductRow } from "./Table";

type Props = {
  open?: boolean;
  row?: ProductRow | null;
  onClose?: () => void;
  onConfirm?: (delta: number) => void;
};

export default function StockAdjustModal({ open, row, onClose, onConfirm }: Props) {
  const [value, setValue] = React.useState<string>("");

  const handleConfirm = () => {
    const n = Number(value);
    if (!Number.isNaN(n) && n !== 0) {
      onConfirm?.(n);
      setValue("");
    }
  };

  if (!row) return null;

  return (
    <Modal
      isOpen={!!open}
      onClose={onClose}
      title={`Ajustar stock — ${row.name}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button variant="primary" onClick={handleConfirm}>
            Confirmar
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <TextField
          type="number"
          placeholder="Δ Cantidad (ej. +5 o -3)"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          fullWidth
        />
      </div>
    </Modal>
  );
}
