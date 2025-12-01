import { useCallback, type FormEvent } from "react";

import type {
  RepairOrder,
  RepairOrderClosePayload,
  RepairOrderPartsPayload,
  RepairOrderPayload,
} from "@api/repairs";
import {
  appendRepairOrderParts,
  closeRepairOrder,
  createRepairOrder,
  deleteRepairOrder,
  downloadRepairOrderPdf,
  removeRepairOrderPart,
  updateRepairOrder,
} from "@api/repairs";

import { initialRepairForm } from "./repairOrdersBoardConstants";
import type { RepairForm } from "../../../../types/repairs";

type RepairOrderActionsParams = {
  token: string;
  form: RepairForm;
  setForm: (updater: (current: RepairForm) => RepairForm) => void;
  formatError: (err: unknown, fallback: string) => string;
  setError: (value: string | null) => void;
  setMessage: (value: string | null) => void;
  refreshOrders: (
    storeId?: number | null,
    query?: string,
    status?: RepairOrder["status"] | "TODOS",
    from?: string | null,
    to?: string | null,
  ) => Promise<void>;
  onInventoryRefresh?: () => void;
  localStoreId: number | null;
  search: string;
  statusFilter: RepairOrder["status"] | "TODOS";
  orders: RepairOrder[];
  dateFrom: string;
  dateTo: string;
};

type RepairOrderActionsResult = {
  handleCreate: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  handleStatusChange: (order: RepairOrder, status: RepairOrder["status"]) => Promise<void>;
  handleDelete: (order: RepairOrder) => Promise<void>;
  handleDownload: (order: RepairOrder) => Promise<void>;
  handleExportCsv: () => void;
  handleAppendParts: (
    order: RepairOrder,
    parts: RepairOrderPartsPayload["parts"],
  ) => Promise<boolean>; // [PACK37-frontend]
  handleRemovePart: (order: RepairOrder, partId: number) => Promise<boolean>; // [PACK37-frontend]
  handleCloseOrder: (
    order: RepairOrder,
    payload?: RepairOrderClosePayload | undefined,
  ) => Promise<boolean>; // [PACK37-frontend]
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
  dateFrom,
  dateTo,
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
      const partsPayload: RepairOrderPartsPayload["parts"] = [];
      for (const part of form.parts) {
        const source = part.source ?? "STOCK";
        const trimmedName = part.partName?.trim() ?? "";
        if (source === "STOCK" && !part.deviceId) {
          setError("Selecciona un dispositivo para cada repuesto tomado del inventario.");
          return;
        }
        if (source === "EXTERNAL" && trimmedName.length === 0) {
          setError("Describe el repuesto externo para registrar su compra.");
          return;
        }
        const payloadPart: RepairOrderPartsPayload["parts"][number] = {
          source,
          quantity: Math.max(1, part.quantity),
          unit_cost: Number.isFinite(part.unitCost) ? Math.max(0, part.unitCost) : 0,
        };
        if (source === "STOCK" && part.deviceId) {
          payloadPart.device_id = part.deviceId;
        }
        if (source === "EXTERNAL") {
          payloadPart.part_name = trimmedName;
        } else if (trimmedName) {
          payloadPart.part_name = trimmedName;
        }
        partsPayload.push(payloadPart);
      }
      const payload: RepairOrderPayload = {
        store_id: form.storeId,
        technician_name: form.technicianName.trim(),
        damage_type: form.damageType.trim(),
        device_description: form.deviceDescription.trim(),
        problem_description: form.problemDescription.trim(),
        estimated_cost: form.estimatedCost,
        deposit_amount: form.depositAmount,
        parts: partsPayload,
        customer_id: form.customerId ?? null,
      };

      const trimmedCustomerName = form.customerName.trim();
      if (trimmedCustomerName) {
        payload.customer_name = trimmedCustomerName;
      }

      const trimmedContact = form.customerContact.trim();
      if (trimmedContact) {
        payload.customer_contact = trimmedContact;
      }

      const trimmedDiagnosis = form.diagnosis.trim();
      if (trimmedDiagnosis) {
        payload.diagnosis = trimmedDiagnosis;
      }

      const trimmedModel = form.deviceModel.trim();
      if (trimmedModel) {
        payload.device_model = trimmedModel;
      }

      const trimmedImei = form.imei.trim();
      if (trimmedImei) {
        payload.imei = trimmedImei;
      }

      const trimmedNotes = form.notes.trim();
      if (trimmedNotes) {
        payload.notes = trimmedNotes;
      }

      const sanitizedLabor = Number.isFinite(form.laborCost) ? Math.max(0, form.laborCost) : undefined;
      if (typeof sanitizedLabor === "number") {
        payload.labor_cost = sanitizedLabor;
      }
      try {
        setError(null);
  await createRepairOrder(token, payload, reason);
        setMessage("Orden de reparación registrada correctamente.");
        setForm((current) => ({ ...initialRepairForm, storeId: current.storeId }));
        await refreshOrders(
          form.storeId,
          search.trim(),
          statusFilter,
          dateFrom.trim() || null,
          dateTo.trim() || null,
        );
        void onInventoryRefresh?.();
      } catch (err) {
        setError(formatError(err, "No fue posible registrar la orden de reparación."));
      }
    },
    [
      askReason,
      dateFrom,
      dateTo,
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
        await refreshOrders(
          localStoreId,
          search.trim(),
          statusFilter,
          dateFrom.trim() || null,
          dateTo.trim() || null,
        );
        void onInventoryRefresh?.();
      } catch (err) {
        setError(formatError(err, "No fue posible actualizar la reparación."));
      }
    },
    [
      askReason,
      dateFrom,
      dateTo,
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
        await refreshOrders(
          localStoreId,
          search.trim(),
          statusFilter,
          dateFrom.trim() || null,
          dateTo.trim() || null,
        );
        void onInventoryRefresh?.();
      } catch (err) {
        setError(formatError(err, "No fue posible eliminar la orden de reparación."));
      }
    },
    [
      askReason,
      dateFrom,
      dateTo,
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

  const handleAppendParts = useCallback(
    async (order: RepairOrder, parts: RepairOrderPartsPayload["parts"]) => {
      if (parts.length === 0) {
        return false;
      }
      const reason = askReason("Motivo corporativo para agregar repuestos a la reparación");
      if (!reason) {
        return false;
      }
      try {
        await appendRepairOrderParts(token, order.id, { parts }, reason);
        setMessage("Repuestos agregados correctamente.");
        await refreshOrders(
          localStoreId,
          search.trim(),
          statusFilter,
          dateFrom.trim() || null,
          dateTo.trim() || null,
        );
        void onInventoryRefresh?.();
        return true;
      } catch (err) {
        setError(formatError(err, "No fue posible agregar los repuestos."));
        return false;
      }
    },
    [
      askReason,
      dateFrom,
      dateTo,
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

  const handleRemovePart = useCallback(
    async (order: RepairOrder, partId: number) => {
      if (!window.confirm(`¿Quitar el repuesto seleccionado de la reparación #${order.id}?`)) {
        return false;
      }
      const reason = askReason("Motivo corporativo para quitar el repuesto de la reparación");
      if (!reason) {
        return false;
      }
      try {
        await removeRepairOrderPart(token, order.id, partId, reason);
        setMessage("Repuesto eliminado correctamente.");
        await refreshOrders(
          localStoreId,
          search.trim(),
          statusFilter,
          dateFrom.trim() || null,
          dateTo.trim() || null,
        );
        void onInventoryRefresh?.();
        return true;
      } catch (err) {
        setError(formatError(err, "No fue posible quitar el repuesto."));
        return false;
      }
    },
    [
      askReason,
      dateFrom,
      dateTo,
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

  const handleCloseOrder = useCallback(
    async (order: RepairOrder, payload?: RepairOrderClosePayload) => {
      const reason = askReason("Motivo corporativo para cerrar la reparación y generar el PDF");
      if (!reason) {
        return false;
      }
      try {
        const blob = await closeRepairOrder(token, order.id, payload, reason);
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `orden_reparacion_${order.id}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        setMessage("Reparación cerrada y PDF generado correctamente.");
        await refreshOrders(
          localStoreId,
          search.trim(),
          statusFilter,
          dateFrom.trim() || null,
          dateTo.trim() || null,
        );
        void onInventoryRefresh?.();
        return true;
      } catch (err) {
        setError(formatError(err, "No fue posible cerrar la reparación."));
        return false;
      }
    },
    [
      askReason,
      dateFrom,
      dateTo,
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

  return {
    handleCreate,
    handleStatusChange,
    handleDelete,
    handleDownload,
    handleExportCsv,
    handleAppendParts,
    handleRemovePart,
    handleCloseOrder,
  };
};

export type { RepairOrderActionsParams, RepairOrderActionsResult };
export default useRepairOrderActions;
