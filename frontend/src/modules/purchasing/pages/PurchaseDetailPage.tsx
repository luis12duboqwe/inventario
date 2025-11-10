import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import {
  POActionsBar,
  POAttachments,
  POHeader,
  POInvoicesTable,
  POItemsTable,
  POReceiptsTable,
  POSupplierCard,
  POTimeline,
  POTotalsCard,
} from "../components/po-detail";
import { ReceiveModal } from "../components/receiving";
import { LandedCostModal, RTVModal, SupplierInvoiceModal } from "../components/supplier-docs";
import {
  cancelPurchaseOrder,
  getPurchaseOrder,
  receivePurchaseOrder,
  sendPurchaseOrderEmail,
  transitionPurchaseOrderStatus,
  uploadPurchaseOrderDocument,
  type PurchaseOrder,
  type PurchaseOrderItem,
  type PurchaseOrderStatus,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

const STATUS_LABELS: Record<PurchaseOrderStatus, string> = {
  BORRADOR: "Borrador",
  PENDIENTE: "Pendiente",
  APROBADA: "Aprobada",
  ENVIADA: "Enviada al proveedor",
  PARCIAL: "Recepción parcial",
  COMPLETADA: "Completada",
  CANCELADA: "Cancelada",
};

type ReceivePayload = {
  qtys: Record<string, number>;
  serials: Record<string, string[]>;
};

const noticeStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  border: "1px solid rgba(148, 163, 184, 0.25)",
  background: "rgba(30, 41, 59, 0.6)",
  color: "#cbd5f5",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const errorStyle: React.CSSProperties = {
  ...noticeStyle,
  border: "1px solid rgba(248, 113, 113, 0.45)",
  background: "rgba(248, 113, 113, 0.12)",
  color: "#fecaca",
};

function buildItemLabel(device: { sku: string; name: string } | undefined, item: PurchaseOrderItem): string {
  if (device) {
    return `${device.sku} · ${device.name}`;
  }
  return `Producto #${item.device_id}`;
}

function PurchaseDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { devices, token, setError: setDashError, pushToast } = useDashboard();
  const [order, setOrder] = useState<PurchaseOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [receiveOpen, setReceiveOpen] = useState(false);
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [rtvOpen, setRtvOpen] = useState(false);
  const [landedCostOpen, setLandedCostOpen] = useState(false);
  const [processingReceive, setProcessingReceive] = useState(false);
  const [processingCancel, setProcessingCancel] = useState(false);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);

  const numericId = Number(orderId);

  const deviceLookup = useMemo(
    () =>
      new Map(
        devices.map((device) => [
          device.id,
          { sku: device.sku, name: device.name, imei: device.imei, serial: device.serial },
        ]),
      ),
    [devices],
  );

  const loadOrder = useCallback(async () => {
    if (!Number.isFinite(numericId)) {
      setError("Identificador de orden inválido.");
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await getPurchaseOrder(token, numericId);
      setOrder(data);
      setError(null);
    } catch (err) {
      const friendly =
        err instanceof Error ? err.message : "No fue posible consultar la orden de compra.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setLoading(false);
    }
  }, [setDashError, token, numericId]);

  useEffect(() => {
    void loadOrder();
  }, [loadOrder]);

  const itemsView = useMemo(() => {
    if (!order) {
      return [];
    }
    return order.items.map((item) => {
      const device = deviceLookup.get(item.device_id);
      const base = {
        id: String(item.id),
        name: buildItemLabel(device, item),
        qty: item.quantity_ordered,
        received: item.quantity_received,
        unitCost: item.unit_cost,
        subtotal: item.quantity_ordered * item.unit_cost,
      } as {
        id: string;
        name: string;
        qty: number;
        received: number;
        unitCost: number;
        subtotal: number;
        sku?: string;
      };
      if (device?.sku) {
        base.sku = device.sku;
      }
      return base;
    });
  }, [deviceLookup, order]);

  const totals = useMemo(() => {
    if (!order) {
      return { subtotal: 0, total: 0, taxes: 0, received: 0 };
    }
    const subtotal = order.items.reduce(
      (sum, item) => sum + item.quantity_ordered * item.unit_cost,
      0,
    );
    const received = order.items.reduce(
      (sum, item) => sum + item.quantity_received * item.unit_cost,
      0,
    );
    return { subtotal, total: subtotal, taxes: 0, received };
  }, [order]);

  const receiptsView = useMemo(() => {
    if (!order) {
      return [];
    }
    const timestamp = order.updated_at || order.created_at;
    return order.items
      .filter((item) => item.quantity_received > 0)
      .map((item) => {
        const device = deviceLookup.get(item.device_id);
        const base = {
          id: `rec-${item.id}`,
          date: timestamp,
          lines: 1,
          qty: item.quantity_received,
        };
        if (device) {
          return { ...base, note: `Recepción de ${device.sku}` };
        }
        return base;
      })
      .sort((a, b) => {
        const first = new Date(a.date).getTime();
        const second = new Date(b.date).getTime();
        if (Number.isNaN(first) && Number.isNaN(second)) {
          return 0;
        }
        if (Number.isNaN(first)) {
          return 1;
        }
        if (Number.isNaN(second)) {
          return -1;
        }
        return first - second;
      });
  }, [deviceLookup, order]);

  const attachmentsView = useMemo(() => {
    if (!order) {
      return [];
    }
    return (order.documents ?? []).map((document) => ({
      id: String(document.id),
      name: document.filename,
      url: document.download_url ?? undefined,
    }));
  }, [order]);

  const timelineView = useMemo(() => {
    if (!order) {
      return [];
    }
    const statusEvents = (order.status_history ?? []).map((event) => {
      const label = STATUS_LABELS[event.status] ?? event.status;
      const details: string[] = [];
      if (event.created_by_name) {
        details.push(event.created_by_name);
      }
      if (event.note) {
        details.push(event.note);
      }
      const message = details.length > 0 ? `${label} · ${details.join(" · ")}` : label;
      return {
        id: `status-${event.id}`,
        date: event.created_at,
        message,
      };
    });

    const returnEvents = (order.returns ?? []).map((entry) => {
      const device = deviceLookup.get(entry.device_id);
      const label = device ? `${device.sku} · ${device.name}` : `Producto #${entry.device_id}`;
      return {
        id: `return-${entry.id}`,
        date: entry.created_at,
        message: `Devolución de ${entry.quantity} unidad(es) (${label})`,
      };
    });

    return [...statusEvents, ...returnEvents]
      .map((event) => {
        const parsed = new Date(event.date);
        const sortKey = Number.isNaN(parsed.getTime()) ? Number.MAX_SAFE_INTEGER : parsed.getTime();
        return { ...event, sortKey };
      })
      .sort((a, b) => a.sortKey - b.sortKey)
      .map((event) => ({ id: event.id, date: event.date, message: event.message }));
  }, [deviceLookup, order]);

  const modalLines = useMemo(() => {
    if (!order) {
      return [];
    }
    return order.items.map((item) => {
      const device = deviceLookup.get(item.device_id);
      const allowSerial = Boolean(device?.imei || device?.serial);
      const line = {
        id: String(item.id),
        name: buildItemLabel(device, item),
        qtyOrdered: item.quantity_ordered,
        qtyReceived: item.quantity_received,
        allowSerial,
      } as {
        id: string;
        name: string;
        qtyOrdered: number;
        qtyReceived: number;
        allowSerial: boolean;
        sku?: string;
      };
      if (device?.sku) {
        line.sku = device.sku;
      }
      return line;
    });
  }, [deviceLookup, order]);

  const statusLabel = order ? STATUS_LABELS[order.status] ?? order.status : "";
  const canReceiveStatuses: PurchaseOrderStatus[] = [
    "PENDIENTE",
    "APROBADA",
    "ENVIADA",
    "PARCIAL",
  ];
  const canReceive = Boolean(order && canReceiveStatuses.includes(order.status));
  const canCancel = Boolean(order && !["COMPLETADA", "CANCELADA"].includes(order.status));

  const handleReceiveSubmit = async ({ qtys }: ReceivePayload) => {
    if (!order) {
      return;
    }
    const items = order.items
      .map((item) => ({
        device_id: item.device_id,
        quantity: qtys[String(item.id)] ?? 0,
      }))
      .filter((entry) => entry.quantity > 0);
    if (items.length === 0) {
      setError("Indica al menos una línea con unidades a recibir.");
      return;
    }
    const reason = window.prompt(
      "Motivo corporativo para registrar la recepción",
      "Recepción parcial de orden",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido.");
      return;
    }
    try {
      setProcessingReceive(true);
      await receivePurchaseOrder(token, order.id, { items }, reason.trim());
      setReceiveOpen(false);
      setMessage("Recepción registrada correctamente.");
      pushToast?.({ message: "Orden recibida", variant: "success" });
      await loadOrder();
    } catch (err) {
      const friendly =
        err instanceof Error ? err.message : "No fue posible registrar la recepción.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setProcessingReceive(false);
    }
  };

  const handleCancel = async () => {
    if (!order) {
      return;
    }
    const reason = window.prompt(
      "Motivo corporativo para cancelar la orden",
      "Cancelación de orden de compra",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido.");
      return;
    }
    try {
      setProcessingCancel(true);
      await cancelPurchaseOrder(token, order.id, reason.trim());
      setMessage("Orden cancelada correctamente.");
      pushToast?.({ message: "Orden cancelada", variant: "info" });
      await loadOrder();
    } catch (err) {
      const friendly = err instanceof Error ? err.message : "No fue posible cancelar la orden.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setProcessingCancel(false);
    }
  };

  const handleOpenReceiveDialog = useCallback(() => {
    setReceiveOpen(true);
  }, []);

  const handleOpenInvoiceDialog = useCallback(() => {
    setInvoiceOpen(true);
    pushToast?.({
      message: "Registro de facturas disponible desde el módulo corporativo de compras",
      variant: "info",
    });
  }, [pushToast]);

  const handleOpenRtvDialog = useCallback(() => {
    setRtvOpen(true);
    pushToast?.({
      message: "Devolución a proveedor disponible desde el módulo corporativo de compras",
      variant: "info",
    });
  }, [pushToast]);

  const handleOpenLandedCostDialog = useCallback(() => {
    setLandedCostOpen(true);
    pushToast?.({
      message: "Costos indirectos disponible desde el módulo corporativo de compras",
      variant: "info",
    });
  }, [pushToast]);

  const handleAttachmentUpload = useCallback(
    async (file: File) => {
      if (!order) {
        return;
      }
      if (file.type !== "application/pdf") {
        setError("Solo se permiten documentos PDF.");
        return;
      }
      const reason = window.prompt(
        "Motivo corporativo para adjuntar el PDF",
        "Adjuntar documentación de compra",
      );
      if (!reason || reason.trim().length < 5) {
        setError("Debes indicar un motivo corporativo válido.");
        return;
      }
      try {
        setUploadingAttachment(true);
        await uploadPurchaseOrderDocument(token, order.id, file, reason.trim());
        setMessage("Documento adjuntado correctamente.");
        pushToast?.({ message: "PDF adjuntado", variant: "success" });
        await loadOrder();
      } catch (err) {
        const friendly =
          err instanceof Error ? err.message : "No fue posible adjuntar el documento.";
        setError(friendly);
        setDashError(friendly);
      } finally {
        setUploadingAttachment(false);
      }
    },
    [loadOrder, order, pushToast, setDashError, token],
  );

  const handleChangeStatus = useCallback(async () => {
    if (!order) {
      return;
    }
    const manualStatuses: PurchaseOrderStatus[] = [
      "BORRADOR",
      "PENDIENTE",
      "APROBADA",
      "ENVIADA",
    ];
    const nextStatusRaw = window.prompt(
      "Nuevo estado (BORRADOR, PENDIENTE, APROBADA, ENVIADA)",
      order.status,
    );
    if (!nextStatusRaw) {
      return;
    }
    const normalized = nextStatusRaw.trim().toUpperCase();
    if (!manualStatuses.includes(normalized as PurchaseOrderStatus)) {
      setError("Estado inválido. Usa BORRADOR, PENDIENTE, APROBADA o ENVIADA.");
      return;
    }
    const reason = window.prompt(
      "Motivo corporativo para actualizar el estado",
      "Actualización de estado de compra",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido.");
      return;
    }
    try {
      setUpdatingStatus(true);
      await transitionPurchaseOrderStatus(
        token,
        order.id,
        { status: normalized as PurchaseOrderStatus },
        reason.trim(),
      );
      setMessage("Estado actualizado correctamente.");
      pushToast?.({ message: "Estado actualizado", variant: "info" });
      await loadOrder();
    } catch (err) {
      const friendly =
        err instanceof Error ? err.message : "No fue posible actualizar el estado.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setUpdatingStatus(false);
    }
  }, [loadOrder, order, pushToast, setDashError, token]);

  const handleSendEmail = useCallback(async () => {
    if (!order) {
      return;
    }
    const recipientsRaw = window.prompt(
      "Correos destino (separados por coma)",
      "compras@example.com",
    );
    if (!recipientsRaw) {
      return;
    }
    const recipients = recipientsRaw
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    if (recipients.length === 0) {
      setError("Debes indicar al menos un destinatario.");
      return;
    }
    const messageBody = window.prompt("Mensaje opcional", "Adjuntamos la orden de compra");
    try {
      setSendingEmail(true);
      await sendPurchaseOrderEmail(token, order.id, {
        recipients,
        message: messageBody?.trim() || undefined,
        include_documents: true,
      });
      setMessage("Orden enviada por correo electrónico.");
      pushToast?.({ message: "Correo enviado", variant: "success" });
      await loadOrder();
    } catch (err) {
      const friendly = err instanceof Error ? err.message : "No fue posible enviar el correo.";
      setError(friendly);
      setDashError(friendly);
    } finally {
      setSendingEmail(false);
    }
  }, [loadOrder, order, pushToast, setDashError, token]);

  const handleCloseMessage = () => setMessage(null);
  const handleDismissError = () => setError(null);


  if (loading && !order) {
    return <div style={{ padding: 16 }}>Cargando orden de compra…</div>;
  }

  if (!order) {
    return (
      <div style={{ padding: 16 }}>
        {error ? (
          <div style={errorStyle}>
            <span>{error}</span>
            <button type="button" onClick={handleDismissError} style={{ padding: "6px 10px", borderRadius: 8 }}>
              Cerrar
            </button>
          </div>
        ) : (
          <p>No se encontró la orden solicitada.</p>
        )}
      </div>
    );
  }

  const poNumber = `PO-${order.id.toString().padStart(5, "0")}`;

  const headerProps: React.ComponentProps<typeof POHeader> = {
    number: poNumber,
    status: statusLabel,
    supplierName: order.supplier,
    receiveDisabled: processingReceive,
    cancelDisabled: processingCancel,
  };
  if (canReceive) {
    headerProps.onReceive = handleOpenReceiveDialog;
  }
  headerProps.onInvoice = handleOpenInvoiceDialog;
  headerProps.onRTV = handleOpenRtvDialog;
  if (canCancel) {
    headerProps.onCancel = handleCancel;
  }

  const statusChangeBlocked = ["COMPLETADA", "CANCELADA"].includes(order.status);
  const actionsProps: React.ComponentProps<typeof POActionsBar> = {
    receiveDisabled: processingReceive,
    cancelDisabled: processingCancel,
    statusDisabled: updatingStatus || statusChangeBlocked,
    sendDisabled: sendingEmail,
  };
  if (canReceive) {
    actionsProps.onReceive = handleOpenReceiveDialog;
  }
  actionsProps.onInvoice = handleOpenInvoiceDialog;
  actionsProps.onRTV = handleOpenRtvDialog;
  if (canCancel) {
    actionsProps.onCancel = handleCancel;
  }
  if (!statusChangeBlocked) {
    actionsProps.onChangeStatus = handleChangeStatus;
  }
  actionsProps.onSend = handleSendEmail;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {error ? (
        <div role="alert" style={errorStyle}>
          <span>{error}</span>
          <button type="button" onClick={handleDismissError} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Cerrar
          </button>
        </div>
      ) : null}

      {message ? (
        <div role="status" style={noticeStyle}>
          <span>{message}</span>
          <button type="button" onClick={handleCloseMessage} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Cerrar
          </button>
        </div>
      ) : null}

      <POHeader {...headerProps} />

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <POItemsTable items={itemsView} />
          <POReceiptsTable items={receiptsView} />
          <POInvoicesTable items={[]} />
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <POSupplierCard s={{ name: order.supplier }} />
          <div style={{ display: "grid", gap: 8 }}>
            <POTotalsCard
              subtotal={totals.subtotal}
              taxes={totals.taxes}
              total={totals.total}
              receivedValue={totals.received}
            />
            <button
              type="button"
              onClick={handleOpenLandedCostDialog}
              style={{ padding: "8px 12px", borderRadius: 8 }}
            >
              Costos indirectos
            </button>
          </div>
          <POAttachments
            items={attachmentsView}
            onUpload={handleAttachmentUpload}
            uploading={uploadingAttachment}
          />
          <POTimeline items={timelineView} />
        </div>
      </div>

      <POActionsBar {...actionsProps} />

      <ReceiveModal
  open={receiveOpen}
  poNumber={poNumber}
        lines={modalLines}
        onClose={() => setReceiveOpen(false)}
        onSubmit={handleReceiveSubmit}
        loading={processingReceive}
      />

      <SupplierInvoiceModal
        open={invoiceOpen}
        poId={String(order.id)}
        onClose={() => setInvoiceOpen(false)}
        onSubmit={() => {
          setInvoiceOpen(false);
        }}
      />
      <RTVModal
        open={rtvOpen}
        poId={String(order.id)}
        onClose={() => setRtvOpen(false)}
        onSubmit={() => {
          setRtvOpen(false);
        }}
      />
      <LandedCostModal
        open={landedCostOpen}
        poId={String(order.id)}
        onClose={() => setLandedCostOpen(false)}
        onSubmit={() => {
          setLandedCostOpen(false);
        }}
      />
    </div>
  );
}

export default PurchaseDetailPage;
