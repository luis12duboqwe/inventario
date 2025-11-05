import React from "react";
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
  const mov = React.useMemo<MoveDetail | null>(() => null, []);

  const calcSubtotal = React.useCallback(() => {
    const items = Array.isArray(mov?.items) ? mov.items : [];
    return items.reduce((acc, item) => acc + (item.qty || 0) * (item.cost || 0), 0);
  }, [mov]);

  const calcAdjustments = React.useCallback(() => 0, []);
  const calcTotal = React.useCallback(() => calcSubtotal() + calcAdjustments(), [calcAdjustments, calcSubtotal]);

  const handleApprove = React.useCallback(() => {
    // TODO: conectar con aprobación real
  }, []);
  const handleCancel = React.useCallback(() => {
    // TODO: conectar con cancelación real
  }, []);
  const handlePrint = React.useCallback(() => {
    // TODO: conectar con impresión
  }, []);
  const handleExportPDF = React.useCallback(() => {
    // TODO: conectar con exportación PDF
  }, []);

  const safeStatus = mov?.status || "PENDING";

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <MoveHeader
        number={mov?.number ?? ""}
        status={safeStatus}
        type={mov?.type ?? ""}
        onPrint={handlePrint}
        onExportPDF={handleExportPDF}
        onApprove={handleApprove}
        onCancel={handleCancel}
      />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <MoveItemsTable items={mov?.items ?? []} />
          <MoveNotes value={mov?.note ?? ""} />
        </div>
        <div style={{ display: "grid", gap: 12 }}>
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
