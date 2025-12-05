import { useState, useEffect } from "react";
import Modal from "@components/ui/Modal";
import Button from "@components/ui/Button";
import { Store } from "@api/stores";
import { createTransferOrder } from "@api/transfers";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  selectedDeviceIds: number[];
  stores: Store[];
  currentStoreId: number | null;
  token: string;
  onSuccess: () => void;
};

export default function BulkTransferDialog({
  isOpen,
  onClose,
  selectedDeviceIds,
  stores,
  currentStoreId,
  token,
  onSuccess,
}: Props) {
  const [destinationStoreId, setDestinationStoreId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setDestinationStoreId(null);
      setReason("");
      setError(null);
      setLoading(false);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destinationStoreId) {
      setError("Selecciona una sucursal de destino.");
      return;
    }
    if (!currentStoreId) {
      setError("No se ha identificado la sucursal de origen.");
      return;
    }
    if (reason.trim().length < 5) {
      setError("El motivo debe tener al menos 5 caracteres.");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Create transfer order with multiple items
      // Assuming quantity 1 for each selected device ID as they are unique items in this table context
      const items = selectedDeviceIds.map((id) => ({
        device_id: id,
        quantity: 1,
      }));

      await createTransferOrder(
        token,
        {
          origin_store_id: currentStoreId,
          destination_store_id: destinationStoreId,
          reason: reason.trim(),
          items,
        },
        reason.trim(),
      );

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear la transferencia.");
    } finally {
      setLoading(false);
    }
  };

  const availableStores = stores.filter((s) => s.id !== currentStoreId);

  return (
    <Modal
      open={isOpen}
      onClose={onClose}
      title={`Transferir ${selectedDeviceIds.length} dispositivos`}
      size="md"
    >
      <form onSubmit={handleSubmit} className="form-grid">
        <p className="text-sm muted-text mb-4">
          Los dispositivos seleccionados se moverán a una orden de transferencia con estado
          &quot;Solicitada&quot;.
        </p>

        {error && <div className="alert error mb-4">{error}</div>}

        <div className="form-group">
          <label htmlFor="destination-store" className="form-label">
            Sucursal de destino
          </label>
          <select
            id="destination-store"
            className="form-select"
            value={destinationStoreId ?? ""}
            onChange={(e) => setDestinationStoreId(Number(e.target.value) || null)}
            disabled={loading}
            required
          >
            <option value="">Selecciona destino...</option>
            {availableStores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="transfer-reason" className="form-label">
            Motivo corporativo
          </label>
          <textarea
            id="transfer-reason"
            className="form-textarea"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Justificación del traslado..."
            rows={3}
            minLength={5}
            disabled={loading}
            required
          />
        </div>

        <div className="modal-actions flex justify-end gap-2 mt-6">
          <Button variant="ghost" onClick={onClose} disabled={loading} type="button">
            Cancelar
          </Button>
          <Button variant="primary" type="submit" disabled={loading}>
            {loading ? "Procesando..." : "Crear transferencia"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
