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
  type PurchaseOrder,
  type PurchaseOrderItem,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

const STATUS_LABELS: Record<PurchaseOrder["status"], string> = {
  PENDIENTE: "Pendiente",
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
  const dashboard = useDashboard();
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

  const numericId = Number(orderId);

  const deviceLookup = useMemo(
    () =>
      new Map(
        dashboard.devices.map((device) => [
          device.id,
          { sku: device.sku, name: device.name, imei: device.imei, serial: device.serial },
        ]),
      ),
    [dashboard.devices],
  );

  const loadOrder = useCallback(async () => {
    if (!Number.isFinite(numericId)) {
      setError("Identificador de orden inválido.");
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const data = await getPurchaseOrder(dashboard.token, numericId);
      setOrder(data);
      setError(null);
    } catch (err) {
      const friendly =
        err instanceof Error ? err.message : "No fue posible consultar la orden de compra.";
      setError(friendly);
      dashboard.setError(friendly);
    } finally {
      setLoading(false);
    }
  }, [dashboard.setError, dashboard.token, numericId]);

  useEffect(() => {
    void loadOrder();
  }, [loadOrder]);

  const itemsView = useMemo(() => {
    if (!order) {
      return [];
    }
    return order.items.map((item) => {
      const device = deviceLookup.get(item.device_id);
      return {
        id: String(item.id),
        sku: device?.sku,
        name: buildItemLabel(device, item),
        qty: item.quantity_ordered,
        received: item.quantity_received,
        unitCost: item.unit_cost,
        subtotal: item.quantity_ordered * item.unit_cost,
      };
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
        return {
          id: `rec-${item.id}`,
          date: timestamp,
          user: undefined,
          lines: 1,
          qty: item.quantity_received,
          note: device ? `Recepción de ${device.sku}` : undefined,
        };
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

  const timelineView = useMemo(() => {
    if (!order) {
      return [];
    }
    const events: Array<{ id: string; date: string; message: string }> = [
      { id: `created-${order.id}`, date: order.created_at, message: "Orden creada" },
    ];
    if (order.status === "PARCIAL") {
      events.push({
        id: `partial-${order.id}`,
        date: order.updated_at || order.created_at,
        message: "Recepción parcial registrada",
      });
    }
    if (order.status === "COMPLETADA") {
      events.push({
        id: `completed-${order.id}`,
        date: order.closed_at || order.updated_at || order.created_at,
        message: "Orden recibida por completo",
      });
    }
    if (order.status === "CANCELADA") {
      events.push({
        id: `cancelled-${order.id}`,
        date: order.updated_at || order.created_at,
        message: "Orden cancelada",
      });
    }
    (order.returns ?? []).forEach((entry) => {
      const device = deviceLookup.get(entry.device_id);
      const label = device ? `${device.sku} · ${device.name}` : `Producto #${entry.device_id}`;
      events.push({
        id: `return-${entry.id}`,
        date: entry.created_at,
        message: `Devolución de ${entry.quantity} unidad(es) (${label})`,
      });
    });
    return events
      .map((event) => {
        const parsed = new Date(event.date);
        const sortKey = Number.isNaN(parsed.getTime()) ? Number.MAX_SAFE_INTEGER : parsed.getTime();
        return { ...event, sortKey };
      })
      .sort((a, b) => a.sortKey - b.sortKey)
      .map(({ sortKey, ...event }) => event);
  }, [deviceLookup, order]);

  const modalLines = useMemo(() => {
    if (!order) {
      return [];
    }
    return order.items.map((item) => {
      const device = deviceLookup.get(item.device_id);
      const allowSerial = Boolean(device?.imei || device?.serial);
      return {
        id: String(item.id),
        name: buildItemLabel(device, item),
        sku: device?.sku,
        qtyOrdered: item.quantity_ordered,
        qtyReceived: item.quantity_received,
        allowSerial,
      };
    });
  }, [deviceLookup, order]);

  const statusLabel = order ? STATUS_LABELS[order.status] ?? order.status : "";
  const canReceive = Boolean(order && ["PENDIENTE", "PARCIAL"].includes(order.status));
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
      await receivePurchaseOrder(dashboard.token, order.id, { items }, reason.trim());
      setReceiveOpen(false);
      setMessage("Recepción registrada correctamente.");
      dashboard.pushToast?.({ message: "Orden recibida", variant: "success" });
      await loadOrder();
    } catch (err) {
      const friendly =
        err instanceof Error ? err.message : "No fue posible registrar la recepción.";
      setError(friendly);
      dashboard.setError(friendly);
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
      await cancelPurchaseOrder(dashboard.token, order.id, reason.trim());
      setMessage("Orden cancelada correctamente.");
      dashboard.pushToast?.({ message: "Orden cancelada", variant: "info" });
      await loadOrder();
    } catch (err) {
      const friendly = err instanceof Error ? err.message : "No fue posible cancelar la orden.";
      setError(friendly);
      dashboard.setError(friendly);
    } finally {
      setProcessingCancel(false);
    }
  };

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

      <POHeader
        number={`PO-${order.id.toString().padStart(5, "0")}`}
        status={statusLabel}
        supplierName={order.supplier}
        onReceive={canReceive ? () => setReceiveOpen(true) : undefined}
        onInvoice={() => {
          setInvoiceOpen(true);
          dashboard.pushToast?.({
            message: "Registro de facturas disponible desde el módulo corporativo de compras",
            variant: "info",
          });
        }}
        onRTV={() => {
          setRtvOpen(true);
          dashboard.pushToast?.({
            message: "Devolución a proveedor disponible desde el módulo corporativo de compras",
            variant: "info",
          });
        }}
        onCancel={canCancel ? handleCancel : undefined}
        receiveDisabled={processingReceive}
        cancelDisabled={processingCancel}
      />

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
              onClick={() => {
                setLandedCostOpen(true);
                dashboard.pushToast?.({
                  message: "Costos indirectos disponible desde el módulo corporativo de compras",
                  variant: "info",
                });
              }}
              style={{ padding: "8px 12px", borderRadius: 8 }}
            >
              Costos indirectos
            </button>
          </div>
          <POAttachments items={[]} />
          <POTimeline items={timelineView} />
        </div>
      </div>

      <POActionsBar
        onReceive={canReceive ? () => setReceiveOpen(true) : undefined}
        onInvoice={() => {
          setInvoiceOpen(true);
          dashboard.pushToast?.({
            message: "Registro de facturas disponible desde el módulo corporativo de compras",
            variant: "info",
          });
        }}
        onRTV={() => {
          setRtvOpen(true);
          dashboard.pushToast?.({
            message: "Devolución a proveedor disponible desde el módulo corporativo de compras",
            variant: "info",
          });
        }}
        onCancel={canCancel ? handleCancel : undefined}
        receiveDisabled={processingReceive}
        cancelDisabled={processingCancel}
      />

      <ReceiveModal
        open={receiveOpen}
        poNumber={`PO-${order.id.toString().padStart(5, "0")}`}
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
