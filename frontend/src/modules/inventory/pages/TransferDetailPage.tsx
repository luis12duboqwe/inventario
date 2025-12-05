import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import PageHeader from "../../../components/layout/PageHeader";
import {
  TransferHeader,
  TransferItemsTable,
  TransferTimeline,
  TransferActionsBar,
  PickModal,
  PackModal,
  ShipModal,
  ReceiveModal,
} from "../components/transfers/detail";
import type {
  PickLine,
  ReceiveLine,
  TimelineStep,
  TransferItemLine,
} from "../components/transfers/detail";
import {
  getTransfer,
  dispatchTransferOrder,
  receiveTransferOrder,
  cancelTransferOrder,
  type TransferOrder,
} from "../../../api/transfers";
import { useAuth } from "../../../auth/useAuth";
import { useDashboard } from "../../../dashboard/context/DashboardContext";
import { emitClientError } from "../../../utils/clientLog";

function TransferDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const { pushToast } = useDashboard();
  const [transferData, setTransferData] = useState<TransferOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setLoading(true);
    setRefreshKey((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (!id || !token) return;
    // Loading is initialized to true, and set to true on refresh
    getTransfer(token, parseInt(id))
      .then((data) => {
        setTransferData(data);
        setLoading(false);
      })
      .catch((err) => {
        emitClientError("TransferDetailPage", "Error loading transfer", err);
        setError("Error al cargar la transferencia");
        setLoading(false);
      });
  }, [id, token, refreshKey]);

  const transfer = useMemo<{
    number?: string;
    status?: string;
    from?: string;
    to?: string;
    items?: TransferItemLine[];
    steps?: TimelineStep[];
  }>(() => {
    if (!transferData) return { items: [], steps: [] };

    const steps: TimelineStep[] = [
      {
        id: "created",
        label: "Solicitada",
        date: transferData.created_at,
        completed: true,
        active: transferData.status === "SOLICITADA",
      },
      {
        id: "dispatched",
        label: "En Tránsito",
        date: transferData.dispatched_at,
        completed: !!transferData.dispatched_at,
        active: transferData.status === "EN_TRANSITO",
      },
      {
        id: "received",
        label: "Recibida",
        date: transferData.received_at,
        completed: !!transferData.received_at,
        active: transferData.status === "RECIBIDA",
      },
    ];

    if (transferData.status === "CANCELADA") {
      steps.push({
        id: "cancelled",
        label: "Cancelada",
        date: transferData.cancelled_at,
        completed: true,
        active: true,
        description: "La transferencia fue cancelada.",
      });
    }

    const items: TransferItemLine[] = (transferData.items || []).map((item) => ({
      id: item.id.toString(),
      sku: item.sku || "N/A",
      name: item.device_name || "Desconocido",
      qty: item.quantity,
      picked: item.dispatched_quantity || 0,
      packed: item.dispatched_quantity || 0,
      shipped: item.dispatched_quantity || 0,
      received: item.received_quantity || 0,
      imeis: [], // TODO: Add IMEIs if available
    }));

    return {
      number: `TR-${transferData.id.toString().padStart(6, "0")}`,
      status: transferData.status,
      from: transferData.origin_store_name,
      to: transferData.destination_store_name,
      items,
      steps,
    };
  }, [transferData]);

  const [pickOpen, setPickOpen] = useState(false);
  const [packOpen, setPackOpen] = useState(false);
  const [shipOpen, setShipOpen] = useState(false);
  const [receiveOpen, setReceiveOpen] = useState(false);

  const pickLines = useMemo<PickLine[]>(() => {
    if (!Array.isArray(transfer.items)) {
      return [];
    }
    return transfer.items.map((item) => ({
      id: item.id,
      name: item.name,
      qty: item.qty,
      picked: item.picked ?? 0,
    }));
  }, [transfer.items]);

  const receiveLines = useMemo<ReceiveLine[]>(() => {
    if (!Array.isArray(transfer.items)) {
      return [];
    }
    return transfer.items.map((item) => ({
      id: item.id,
      name: item.name,
      qty: item.qty,
      shipped: item.shipped ?? 0,
      allowSerial: Boolean(item.imeis && item.imeis.length > 0),
    }));
  }, [transfer.items]);

  const handleDispatch = async (payload: { carrier: string; tracking: string }) => {
    if (!token || !id) return;
    try {
      const reason = `Despacho: ${payload.carrier} - ${payload.tracking}`;
      await dispatchTransferOrder(token, parseInt(id), { reason }, reason);
      setShipOpen(false);
      refresh();
      pushToast({ message: "Transferencia despachada exitosamente", variant: "success" });
    } catch (err) {
      emitClientError("TransferDetailPage", "Error dispatching transfer", err);
      pushToast({ message: "Error al despachar la transferencia", variant: "danger" });
    }
  };

  const handleReceive = async (payload: {
    qtys: Record<string, number>;
    serials: Record<string, string[]>;
  }) => {
    if (!token || !id) return;
    try {
      const reason = "Recepción de transferencia";
      const items = Object.entries(payload.qtys).map(([itemId, qty]) => ({
        item_id: parseInt(itemId),
        received_quantity: qty,
      }));
      await receiveTransferOrder(token, parseInt(id), { reason, items }, reason);
      setReceiveOpen(false);
      refresh();
      pushToast({ message: "Transferencia recibida exitosamente", variant: "success" });
    } catch (err) {
      emitClientError("TransferDetailPage", "Error receiving transfer", err);
      pushToast({ message: "Error al recibir la transferencia", variant: "danger" });
    }
  };

  const handleCancel = async () => {
    if (!token || !id) return;
    const reason = window.prompt("Motivo de cancelación:");
    if (!reason) return;
    try {
      await cancelTransferOrder(token, parseInt(id), { reason }, reason);
      refresh();
      pushToast({ message: "Transferencia cancelada", variant: "info" });
    } catch (err) {
      emitClientError("TransferDetailPage", "Error cancelling transfer", err);
      pushToast({ message: "Error al cancelar la transferencia", variant: "danger" });
    }
  };

  const handlePrint = async () => {
    window.print();
  };

  if (loading && !transferData) {
    return (
      <div className="inventory-page">
        <PageHeader title="Detalle de transferencia" subtitle="Cargando..." />
        <div className="p-4 text-center">Cargando información...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="inventory-page">
        <PageHeader title="Detalle de transferencia" subtitle="Error" />
        <div className="p-4 text-center text-danger">{error}</div>
      </div>
    );
  }

  if (!transferData) {
    return (
      <div className="inventory-page">
        <PageHeader title="Detalle de transferencia" subtitle="No encontrada" />
        <div className="p-4 text-center">No se encontró la transferencia solicitada.</div>
      </div>
    );
  }

  return (
    <div className="inventory-page">
      <PageHeader title="Detalle de transferencia" subtitle="Seguimiento y acciones operativas." />

      <TransferHeader
        number={transfer.number ?? ""}
        status={transfer.status ?? "SOLICITADA"}
        from={transfer.from ?? ""}
        to={transfer.to ?? ""}
        onPick={() => setPickOpen(true)}
        onPack={() => setPackOpen(true)}
        onShip={() => setShipOpen(true)}
        onReceive={() => setReceiveOpen(true)}
        onCancel={handleCancel}
      />

      <TransferTimeline steps={transfer.steps ?? []} />

      <TransferItemsTable items={transfer.items ?? []} />

      <TransferActionsBar
        onPick={() => setPickOpen(true)}
        onPack={() => setPackOpen(true)}
        onShip={() => setShipOpen(true)}
        onReceive={() => setReceiveOpen(true)}
        onPrint={handlePrint}
      />

      <PickModal
        open={pickOpen}
        lines={pickLines}
        onClose={() => setPickOpen(false)}
        onSubmit={() => {
          // Picked: payload

          setPickOpen(false);
          setPackOpen(true);
          pushToast({ message: "Picking completado (simulado)", variant: "success" });
        }}
      />

      <PackModal
        open={packOpen}
        onClose={() => setPackOpen(false)}
        onSubmit={() => {
          // Packed: payload

          setPackOpen(false);
          setShipOpen(true);
          pushToast({ message: "Packing completado (simulado)", variant: "success" });
        }}
      />

      <ShipModal open={shipOpen} onClose={() => setShipOpen(false)} onSubmit={handleDispatch} />

      <ReceiveModal
        open={receiveOpen}
        lines={receiveLines}
        onClose={() => setReceiveOpen(false)}
        onSubmit={handleReceive}
      />
    </div>
  );
}

export default TransferDetailPage;
