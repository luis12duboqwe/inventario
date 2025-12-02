import React, { useState } from "react";
import { Lock, AlertTriangle } from "lucide-react";
import Modal from "@components/ui/Modal";
import TextField from "@components/ui/TextField";
import Button from "@components/ui/Button";

interface CloseCashSessionModalProps {
  session: {
    initial_cash: number;
    total_sales_cash: number;
    total_sales_card: number;
    total_sales_transfer: number;
  };
  onClose: () => void;
  onConfirm: (finalCash: number, notes: string) => void;
}

export const CloseCashSessionModal: React.FC<CloseCashSessionModalProps> = ({
  session,
  onClose,
  onConfirm,
}) => {
  const [finalCash, setFinalCash] = useState("");
  const [notes, setNotes] = useState("");

  const expectedCash = session.initial_cash + session.total_sales_cash;
  const difference = Number(finalCash) - expectedCash;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(Number(finalCash), notes);
  };

  return (
    <Modal open={true} onClose={onClose} title="Cerrar Caja" size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="bg-slate-900 p-3 rounded border border-slate-700">
            <div className="text-xs text-slate-400">Fondo Inicial</div>
            <div className="font-mono text-lg">${session.initial_cash.toLocaleString()}</div>
          </div>
          <div className="bg-slate-900 p-3 rounded border border-slate-700">
            <div className="text-xs text-slate-400">Ventas Efectivo</div>
            <div className="font-mono text-lg text-green-400">
              +${session.total_sales_cash.toLocaleString()}
            </div>
          </div>
          <div className="bg-slate-900 p-3 rounded border border-slate-700 col-span-2">
            <div className="text-xs text-slate-400">Total Esperado en Caja</div>
            <div className="font-mono text-xl font-bold text-blue-400">
              ${expectedCash.toLocaleString()}
            </div>
          </div>
        </div>

        <TextField
          label="Efectivo Real en Caja"
          type="number"
          value={finalCash}
          onChange={(e) => setFinalCash(e.target.value)}
          required
          min="0"
          step="0.01"
          placeholder="0.00"
        />

        {finalCash && Math.abs(difference) > 0.01 && (
          <div
            className={`p-3 rounded border flex items-start gap-2 ${
              difference < 0
                ? "bg-red-900/20 border-red-800 text-red-200"
                : "bg-yellow-900/20 border-yellow-800 text-yellow-200"
            }`}
          >
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <div>
              <div className="font-semibold">Diferencia detectada</div>
              <div>
                {difference < 0 ? "Faltante" : "Sobrante"} de $
                {Math.abs(difference).toLocaleString()}
              </div>
            </div>
          </div>
        )}

        <TextField
          label="Notas de Cierre"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Observaciones sobre el cierre..."
          multiline
          rows={2}
        />

        <div className="flex justify-end gap-2 pt-4">
          <Button variant="ghost" onClick={onClose} type="button">
            Cancelar
          </Button>
          <Button variant="danger" type="submit">
            <Lock className="w-4 h-4 mr-2" />
            Confirmar Cierre
          </Button>
        </div>
      </form>
    </Modal>
  );
};
