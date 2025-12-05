import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { emitClientError } from "../../../utils/clientLog";
import { useInventoryModule } from "../hooks/useInventoryModule";
import { getMovement } from "@api/inventory";
import type { InventoryMovement } from "@api/inventoryTypes";
import {
  MoveAttachments,
  MoveDestinationCard,
  MoveHeader,
  MoveItemsTable,
  MoveNotes,
  MoveSourceCard,
  MoveTimeline,
  MoveTotalsCard,
} from "../components/move-detail";

type MoveDetail = {
  id: string;
  number?: string;
  status?: string;
  type?: string;
  source?: { id?: string; name?: string };
  dest?: { id?: string; name?: string };
  items?: Array<{ id: string; sku: string; name: string; qty: number; cost?: number }>;
  note?: string;
  events?: Array<{ id: string; date: string; message: string }>;
  attachments?: Array<{ id: string; name: string; url?: string }>;
};

export default function StockMoveDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, selectedStoreId } = useInventoryModule();
  const [loading, setLoading] = useState(false);
  const [movement, setMovement] = useState<InventoryMovement | null>(null);

  useEffect(() => {
    if (!id || !token || !selectedStoreId) return;

    const fetchMovement = async () => {
      setLoading(true);
      try {
        const data = await getMovement(token, selectedStoreId, Number(id));
        setMovement(data);
      } catch (err) {
        emitClientError("StockMoveDetailPage", "Error loading movement", err);
        // pushToast("Error al cargar movimiento", "error"); // pushToast not available here, need to import useDashboard or similar if needed
        // navigate("/inventory/movements"); // navigate not available
      } finally {
        setLoading(false);
      }
    };

    fetchMovement();
  }, [id, token, selectedStoreId]);

  const mov = React.useMemo<MoveDetail | null>(() => {
    if (!movement) return null;
    return {
      id: String(movement.id),
      number: `MOV-${movement.id}`,
      status: "COMPLETED", // Movements are usually completed immediately
      type: movement.tipo_movimiento,
      source: {
        id: String(movement.sucursal_origen_id || ""),
        name: movement.sucursal_origen || "N/A",
      },
      dest: {
        id: String(movement.sucursal_destino_id || ""),
        name: movement.sucursal_destino || "N/A",
      },
      items: [
        {
          id: String(movement.producto_id),
          sku: "N/A", // InventoryMovement doesn't have SKU directly, might need enrichment
          name: `Producto #${movement.producto_id}`, // Placeholder if name not available
          qty: movement.cantidad,
          cost: movement.unit_cost || 0,
        },
      ],
      note: movement.comentario || "",
      events: [
        {
          id: "1",
          date: movement.fecha,
          message: `Movimiento registrado por ${movement.usuario || "Sistema"}`,
        },
      ],
      attachments: [],
    };
  }, [movement]);

  const calcSubtotal = React.useCallback(() => {
    const items = Array.isArray(mov?.items) ? mov.items : [];
    return items.reduce((acc, item) => acc + (item.qty || 0) * (item.cost || 0), 0);
  }, [mov]);

  const calcAdjustments = React.useCallback(() => 0, []);
  const calcTotal = React.useCallback(
    () => calcSubtotal() + calcAdjustments(),
    [calcAdjustments, calcSubtotal],
  );

  const handleApprove = React.useCallback(() => {
    // Not supported for historical movements
    console.warn("Approve action not supported for historical movements");
  }, []);
  const handleCancel = React.useCallback(() => {
    // Not supported for historical movements
    console.warn("Cancel action not supported for historical movements");
  }, []);
  const handlePrint = React.useCallback(() => {
    window.print();
  }, []);
  const handleExportPDF = React.useCallback(() => {
    window.print();
  }, []);

  if (loading) return <div className="p-8 text-center">Cargando movimiento...</div>;
  // if (error) return <div className="p-8 text-center text-red-500">{error}</div>;

  const safeStatus = mov?.status || "PENDING";

  return (
    <div className="stock-move-detail-container">
      <MoveHeader
        number={mov?.number ?? ""}
        status={safeStatus}
        type={mov?.type ?? ""}
        onPrint={handlePrint}
        onExportPDF={handleExportPDF}
        onApprove={handleApprove}
        onCancel={handleCancel}
      />
      <div className="stock-move-detail-grid">
        <div className="stock-move-detail-column">
          <MoveItemsTable items={mov?.items ?? []} />
          <MoveNotes value={mov?.note ?? ""} />
        </div>
        <div className="stock-move-detail-column">
          <MoveSourceCard node={mov?.source ?? { id: "", name: "" }} />
          <MoveDestinationCard node={mov?.dest ?? { id: "", name: "" }} />
          <MoveTotalsCard
            subtotal={calcSubtotal()}
            adjustments={calcAdjustments()}
            total={calcTotal()}
          />
          <MoveTimeline items={mov?.events ?? []} />
          <MoveAttachments items={mov?.attachments ?? []} />
        </div>
      </div>
    </div>
  );
}
