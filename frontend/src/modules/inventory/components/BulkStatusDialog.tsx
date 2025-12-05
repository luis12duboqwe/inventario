import { useState, useEffect } from "react";
import Modal from "@components/ui/Modal";
import Button from "@components/ui/Button";
import { updateDevice } from "@api/inventory";
import { Device } from "@api/inventory";

type Props = {
  open: boolean;
  onClose: () => void;
  selectedDevices: Device[];
  token: string;
  onSuccess: () => void;
};

const STATUS_OPTIONS = [
  "Disponible",
  "En revisión",
  "Defectuoso",
  "Vendido",
  "Reservado",
  "Perdido",
  "Robado",
];

export default function BulkStatusDialog({
  open,
  onClose,
  selectedDevices,
  token,
  onSuccess,
}: Props) {
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (open) {
      setStatus("");
      setReason("");
      setError(null);
      setLoading(false);
      setProgress(0);
    }
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!status) {
      setError("Selecciona un estado.");
      return;
    }
    if (reason.trim().length < 5) {
      setError("El motivo debe tener al menos 5 caracteres.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setProgress(0);

      let completed = 0;
      const errors: string[] = [];

      const promises = selectedDevices.map(async (device) => {
        try {
          await updateDevice(token, device.store_id, device.id, { estado: status }, reason.trim());
          completed++;
          setProgress((completed / selectedDevices.length) * 100);
        } catch (err) {
          console.error(`Error updating device ${device.id}:`, err);
          errors.push(
            `Error en dispositivo ${device.sku}: ${
              err instanceof Error ? err.message : "Desconocido"
            }`,
          );
        }
      });

      await Promise.all(promises);

      if (errors.length > 0) {
        setError(
          `Se actualizaron ${completed} de ${selectedDevices.length}. Errores:\n${errors
            .slice(0, 3)
            .join("\n")}${errors.length > 3 ? "..." : ""}`,
        );
      } else {
        onSuccess();
        onClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al actualizar estados.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Cambiar estado de ${selectedDevices.length} dispositivos`}
      size="md"
    >
      <form onSubmit={handleSubmit} className="form-grid">
        <p className="text-sm muted-text mb-4">
          Actualizará el &quot;Estado de inventario&quot; para todos los ítems seleccionados.
        </p>

        {error && <div className="alert error mb-4 whitespace-pre-wrap">{error}</div>}

        <div className="form-group">
          <label htmlFor="new-status" className="form-label">
            Nuevo estado
          </label>
          <select
            id="new-status"
            className="form-select"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            disabled={loading}
            required
          >
            <option value="">Selecciona estado...</option>
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="status-reason" className="form-label">
            Motivo corporativo
          </label>
          <textarea
            id="status-reason"
            className="form-textarea"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Justificación del cambio..."
            rows={3}
            minLength={5}
            disabled={loading}
            required
          />
        </div>

        {loading && (
          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mb-4">
            <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${progress}%` }}></div>
          </div>
        )}

        <div className="modal-actions flex justify-end gap-2 mt-6">
          <Button variant="ghost" onClick={onClose} disabled={loading} type="button">
            Cancelar
          </Button>
          <Button variant="primary" type="submit" disabled={loading}>
            {loading ? "Procesando..." : "Actualizar estados"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
