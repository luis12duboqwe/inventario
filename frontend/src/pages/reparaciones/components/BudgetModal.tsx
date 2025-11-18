import type { RepairOrder } from "../../../api";
import Modal from "../../../shared/components/ui/Modal";

import type { RepairPartForm } from "../../../types/repairs";

type BudgetModalProps = {
  order: RepairOrder | null;
  open: boolean;
  onClose: () => void;
  onConfirmClose?: (() => Promise<void> | void) | undefined; // [PACK37-frontend]
};

type PartLike = RepairOrder["parts"][number] | RepairPartForm;

function resolveUnitCost(part: PartLike): number {
  if ("unit_cost" in part) {
    return Number(part.unit_cost ?? 0);
  }
  return Number(part.unitCost ?? 0);
}

function resolveQuantity(part: PartLike): number {
  return Number(part.quantity ?? 0);
}

function getPartsTotal(parts: RepairOrder["parts"], fallbackParts: RepairPartForm[] = []) {
  if (parts.length === 0 && fallbackParts.length === 0) {
    return 0;
  }
  const activeParts: PartLike[] = parts.length > 0 ? parts : fallbackParts;
  return activeParts.reduce((acc, part) => acc + resolveUnitCost(part) * resolveQuantity(part), 0);
}

function BudgetModal({ order, open, onClose, onConfirmClose }: BudgetModalProps) {
  if (!order) {
    return null;
  }

  const labor = Number(order.labor_cost ?? 0);
  const partsTotal = getPartsTotal(order.parts);
  const total = Number(order.total_cost ?? labor + partsTotal);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Presupuesto de la reparación #${order.id}`}
      description="Detalle del costo estimado antes de confirmar la orden."
      size="lg"
    >
      <div className="budget-modal">
        <section>
          <h3>Información general</h3>
          <ul className="muted-text">
            <li>
              Cliente: <strong>{order.customer_name ?? "Mostrador"}</strong>
            </li>
            {order.customer_contact ? (
              <li>
                Contacto: <strong>{order.customer_contact}</strong>
              </li>
            ) : null}
            <li>
              Técnico: <strong>{order.technician_name}</strong>
            </li>
            <li>
              Diagnóstico: <strong>{order.damage_type}</strong>
            </li>
            {order.diagnosis ? (
              <li>
                Evaluación técnica: <strong>{order.diagnosis}</strong>
              </li>
            ) : null}
            {order.device_model ? (
              <li>
                Modelo: <strong>{order.device_model}</strong>
              </li>
            ) : null}
            {order.imei ? (
              <li>
                IMEI/Serie: <strong>{order.imei}</strong>
              </li>
            ) : null}
          </ul>
        </section>
        <section>
          <h3>Totales estimados</h3>
          <div className="budget-modal__totals">
            <div>
              <span className="muted-text">Mano de obra</span>
              <strong>${labor.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </div>
            <div>
              <span className="muted-text">Repuestos</span>
              <strong>${partsTotal.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </div>
            <div>
              <span className="muted-text">Total</span>
              <strong>${total.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
            </div>
          </div>
        </section>
        <section>
          <h3>Notas registradas</h3>
          {order.notes ? <p>{order.notes}</p> : <p className="muted-text">Sin notas adicionales.</p>}
        </section>
        {onConfirmClose ? (
          <div className="actions-row">
            <button type="button" className="btn btn--primary" onClick={() => void onConfirmClose()}>
              Cerrar orden y descargar PDF
            </button>
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Volver
            </button>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}

export type { BudgetModalProps };
export default BudgetModal;
