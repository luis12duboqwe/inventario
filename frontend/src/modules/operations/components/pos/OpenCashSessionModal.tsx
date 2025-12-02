import React, { useState } from "react";
import { Unlock } from "lucide-react";
import Modal from "@components/ui/Modal";
import TextField from "@components/ui/TextField";
import Button from "@components/ui/Button";

interface OpenCashSessionModalProps {
  onClose: () => void;
  onConfirm: (initialCash: number, notes: string) => void;
}

export const OpenCashSessionModal: React.FC<OpenCashSessionModalProps> = ({
  onClose,
  onConfirm,
}) => {
  const [initialCash, setInitialCash] = useState("");
  const [notes, setNotes] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(Number(initialCash), notes);
  };

  return (
    <Modal open={true} onClose={onClose} title="Abrir Caja" size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-blue-900/20 p-3 rounded border border-blue-800 text-sm text-blue-200 mb-4">
          Ingresa el monto inicial en efectivo para comenzar las operaciones del día.
        </div>

        <TextField
          label="Fondo Inicial"
          type="number"
          value={initialCash}
          onChange={(e) => setInitialCash(e.target.value)}
          required
          min="0"
          step="0.01"
          placeholder="0.00"
        />

        <TextField
          label="Notas (Opcional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Observaciones iniciales..."
        />

        <div className="flex justify-end gap-2 pt-4">
          <Button variant="ghost" onClick={onClose} type="button">
            Cancelar
          </Button>
          <Button variant="primary" type="submit">
            <Unlock className="w-4 h-4 mr-2" />
            Abrir Caja
          </Button>
        </div>
      </form>
    </Modal>
  );
};
