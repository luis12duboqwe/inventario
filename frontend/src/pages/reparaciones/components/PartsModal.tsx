import type { RepairOrder } from "../../../api";
import Modal from "../../../shared/components/ui/Modal";

type PartsModalProps = {
  order: RepairOrder | null;
  open: boolean;
  onClose: () => void;
  resolveDeviceLabel: (deviceId: number) => string;
};

function PartsModal({ order, open, onClose, resolveDeviceLabel }: PartsModalProps) {
  if (!order) {
    return null;
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Repuestos utilizados · #${order.id}`}
      description="Detalle de piezas descontadas del inventario para la orden seleccionada."
      size="lg"
    >
      {order.parts.length === 0 ? (
        <p className="muted-text">No se registraron repuestos para esta reparación.</p>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Dispositivo</th>
                <th>Cantidad</th>
                <th>Costo unitario</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {order.parts.map((part) => {
                const label = resolveDeviceLabel(part.device_id);
                const total = Number(part.unit_cost ?? 0) * Number(part.quantity ?? 0);
                return (
                  <tr key={`${order.id}-${part.id ?? `${part.device_id}-${part.quantity}`}`}> 
                    <td>{label}</td>
                    <td>{part.quantity}</td>
                    <td>${Number(part.unit_cost ?? 0).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td>${total.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}

export type { PartsModalProps };
export default PartsModal;
