import { useCallback, type FormEvent } from "react";

import type { RepairOrder } from "../../../../api";
import {
  createRepairOrder,
  deleteRepairOrder,
  downloadRepairOrderPdf,
  updateRepairOrder,
} from "../../../../api";

import { initialRepairForm } from "./repairOrdersBoardConstants";
import type { RepairForm } from "./RepairOrdersTypes";

type RepairOrderActionsParams = {
  token: string;
  form: RepairForm;
  setForm: (updater: (current: RepairForm) => RepairForm) => void;
  formatError: (err: unknown, fallback: string) => string;
  setError: (value: string | null) => void;
  setMessage: (value: string | null) => void;
  refreshOrders: (storeId?: number | null, query?: string, status?: RepairOrder["status"] | "TODOS") => Promise<void>;
  onInventoryRefresh?: () => void;
  localStoreId: number | null;
  search: string;
  statusFilter: RepairOrder["status"] | "TODOS";
  orders: RepairOrder[];
};

type RepairOrderActionsResult = {
  handleCreate: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleStatusChange: (order: RepairOrder, status: RepairOrder["status"]) => Promise<void>;
  handleDelete: (order: RepairOrder) => Promise<void>;
  handleDownload: (order: RepairOrder) => Promise<void>;
  handleExportCsv: () => void;
};

const useRepairOrderActions = ({
  token,
  form,
  setForm,
  formatError,
  setError,
  setMessage,
  refreshOrders,
  onInventoryRefresh,
  localStoreId,
  search,
  statusFilter,
  orders,
}: RepairOrderActionsParams): RepairOrderActionsResult => {
  const askReason = useCallback(
    (promptText: string): string | null => {
      const reason = window.prompt(promptText, "");
      if (!reason || reason.trim().length < 5) {
        setError("Debes indicar un motivo corporativo válido (mínimo 5 caracteres).");
        return null;
      }
      return reason.trim();
    },
    [setError],
  );

  const handleCreate = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!form.storeId) {
        setError("Selecciona la sucursal donde se registrará la reparación.");
        return;
      }
      if (!form.technicianName.trim()) {
        setError("Indica el técnico responsable de la orden.");
        return;
      }
      if (!form.damageType.trim()) {
        setError("Describe el tipo de daño reportado.");
        return;
      }
      const reason = askReason("Motivo corporativo para registrar la reparación");
      if (!reason) {
        return;
      }
      const partsPayload = form.parts
        .filter((part) => part.deviceId && part.quantity > 0)
        .map((part) => ({
          device_id: part.deviceId as number,
          quantity: Math.max(1, part.quantity),
          unit_cost: Number.isFinite(part.unitCost) ? Math.max(0, part.unitCost) : 0,
        }));
      const payload = {
        store_id: form.storeId,
        customer_id: form.customerId ?? undefined,
        customer_name: form.customerName.trim() || undefined,
        technician_name: form.technicianName.trim(),
        damage_type: form.damageType.trim(),
        device_description: form.deviceDescription.trim() || undefined,
        notes: form.notes.trim() || undefined,
        labor_cost: Number.isFinite(form.laborCost) ? Math.max(0, form.laborCost) : 0,
        parts: partsPayload,
      };
      try {
        setError(null);
        await createRepairOrder(token, payload, reason);
        setMessage("Orden de reparación registrada correctamente.");
        setForm((current) => ({ ...initialRepairForm, storeId: current.storeId }));
        await refreshOrders(form.storeId, search.trim(), statusFilter);
        void onInventoryRefresh?.();
      } catch (err) {
        setError(formatError(err, "No fue posible registrar la orden de reparación."));
      }
    },
    [
      askReason,
      form,
      formatError,
      onInventoryRefresh,
      refreshOrders,
      search,
      setError,
      setForm,
      setMessage,
      statusFilter,
      token,
    ],
  );

  const handleStatusChange = useCallback(
    async (order: RepairOrder, status: RepairOrder["status"]) => {
      if (status === order.status) {
        return;
      }
      const reason = askReason("Motivo corporativo para actualizar el estado de la reparación");
      if (!reason) {
        return;
      }
      try {
        await updateRepairOrder(token, order.id, { status }, reason);
        setMessage("Estado de reparación actualizado.");
        await refreshOrders(localStoreId, search.trim(), statusFilter);
        void onInventoryRefresh?.();
      } catch (err) {
        setError(formatError(err, "No fue posible actualizar la reparación."));
      }
    },
    [
      askReason,
      formatError,
      localStoreId,
      onInventoryRefresh,
      refreshOrders,
      search,
      setError,
      setMessage,
      statusFilter,
      token,
    ],
  );

  const handleDelete = useCallback(
    async (order: RepairOrder) => {
      if (!window.confirm(`¿Eliminar la reparación #${order.id}?`)) {
        return;
      }
      const reason = askReason("Motivo corporativo para eliminar la orden de reparación");
      if (!reason) {
        return;
      }
      try {
        await deleteRepairOrder(token, order.id, reason);
        setMessage("Orden de reparación eliminada.");
        await refreshOrders(localStoreId, search.trim(), statusFilter);
        void onInventoryRefresh?.();
      } catch (err) {
        setError(formatError(err, "No fue posible eliminar la orden de reparación."));
      }
    },
    [
      askReason,
      formatError,
      localStoreId,
      onInventoryRefresh,
      refreshOrders,
      search,
      setError,
      setMessage,
      statusFilter,
      token,
    ],
  );

  const handleDownload = useCallback(
    async (order: RepairOrder) => {
      try {
        const blob = await downloadRepairOrderPdf(token, order.id);
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `orden_reparacion_${order.id}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } catch (err) {
        setError(formatError(err, "No fue posible descargar la orden en PDF."));
      }
    },
    [formatError, setError, token],
  );

  const handleExportCsv = useCallback(() => {
    const headers = ["id", "cliente", "tecnico", "daño", "estado", "total", "actualizado"];
    const rows = orders.map((order) => [
      order.id,
      order.customer_name ?? "Mostrador",
      order.technician_name,
      order.damage_type,
      order.status,
      order.total_cost,
      order.updated_at,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ordenes_reparacion_${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [orders]);

  return { handleCreate, handleStatusChange, handleDelete, handleDownload, handleExportCsv };
};

export type { RepairOrderActionsParams, RepairOrderActionsResult };
export default useRepairOrderActions;
