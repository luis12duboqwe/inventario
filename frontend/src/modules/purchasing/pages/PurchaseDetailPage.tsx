import React, { useState } from "react";
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

export default function PurchaseDetailPage() {
  const po: any = {}; // TODO(wire)
  const [showReceive, setShowReceive] = useState<boolean>(false);
  const [showInvoice, setShowInvoice] = useState<boolean>(false);
  const [showRTV, setShowRTV] = useState<boolean>(false);
  const [showLandedCost, setShowLandedCost] = useState<boolean>(false);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <POHeader
        number={po?.number}
        status={po?.status}
        supplierName={po?.supplier?.name}
        onReceive={() => setShowReceive(true)}
        onInvoice={() => setShowInvoice(true)}
        onRTV={() => setShowRTV(true)}
        onCancel={() => {
          // TODO(wire)
        }}
      />
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <POItemsTable items={po?.items} />
          <POReceiptsTable items={po?.receipts} />
          <POInvoicesTable items={po?.invoices} />
        </div>
        <div style={{ display: "grid", gap: 12 }}>
          <POSupplierCard s={po?.supplier} />
          <div style={{ display: "grid", gap: 8 }}>
            <POTotalsCard
              subtotal={po?.subtotal || 0}
              taxes={po?.taxes || 0}
              total={po?.total || 0}
              receivedValue={po?.receivedValue}
            />
            <button
              type="button"
              onClick={() => setShowLandedCost(true)}
              style={{ padding: "8px 12px", borderRadius: 8 }}
            >
              Costos indirectos
            </button>
          </div>
          <POAttachments items={po?.attachments} />
          <POTimeline items={po?.events} />
        </div>
      </div>
      <POActionsBar
        onReceive={() => setShowReceive(true)}
        onInvoice={() => setShowInvoice(true)}
        onRTV={() => setShowRTV(true)}
        onCancel={() => {
          // TODO(wire)
        }}
      />
      <ReceiveModal
        open={showReceive}
        poNumber={po?.number}
        lines={po?.items}
        onClose={() => setShowReceive(false)}
        onSubmit={(dto) => {
          // TODO(wire)
        }}
      />
      <SupplierInvoiceModal
        open={showInvoice}
        poId={po?.id}
        onClose={() => setShowInvoice(false)}
        onSubmit={(dto) => {
          // TODO(wire)
        }}
      />
      <RTVModal
        open={showRTV}
        poId={po?.id}
        onClose={() => setShowRTV(false)}
        onSubmit={(dto) => {
          // TODO(wire)
        }}
      />
      <LandedCostModal
        open={showLandedCost}
        poId={po?.id}
        onClose={() => setShowLandedCost(false)}
        onSubmit={(dto) => {
          // TODO(wire)
        }}
      />
    </div>
  );
}
