import React, { useMemo, useState } from "react";

import {
  POAttachments,
  POHeader,
  POItemsTable,
  PONotes,
  POPaymentsTimeline,
  POReceiptsTimeline,
  POSupplierCard,
  POTotalsCard,
} from "../components/po-detail";
import { POCancelModal, POReceiveModal } from "../components/po-list";

const PURCHASE_ORDER_SAMPLE = {
  id: "po-1002",
  number: "PO-2025-0002",
  status: "PARTIAL",
  supplier: {
    name: "Tecno Global",
    contact: "Laura Ponce",
    phone: "+52 55 8000 8000",
    email: "compras@tecnoglobal.mx",
    taxId: "RFC TGL800101XX1",
  },
  items: [
    { id: "line-1", sku: "APL-IP13P-128", name: "iPhone 13 Pro 128GB", cost: 25999, qty: 3, received: 2 },
    { id: "line-2", sku: "SMS-GW6-44", name: "Galaxy Watch 6 44mm", cost: 8899, qty: 4, received: 4 },
    { id: "line-3", sku: "XMI-RN12-128", name: "Redmi Note 12 128GB", cost: 7299, qty: 6, received: 3 },
  ],
  discount: 4500,
  taxRate: 0.16,
  note: "Recepciones escalonadas por disponibilidad del proveedor. Registrar pendiente la última remesa.",
  receipts: [
    { id: "rec-1", date: "2025-02-16T10:30:00", qty: 12 },
    { id: "rec-2", date: "2025-02-18T14:15:00", qty: 5 },
  ],
  payments: [
    { id: "pay-1", date: "2025-02-17T09:00:00", amount: 150000, method: "Transferencia" },
    { id: "pay-2", date: "2025-02-19T12:45:00", amount: 50000, method: "Tarjeta corporativa" },
  ],
  attachments: [
    { id: "file-1", name: "cotizacion-proveedor.pdf", url: "#" },
    { id: "file-2", name: "orden-firmada.pdf", url: "#" },
  ],
};

function PurchaseOrderDetailPage() {
  const po = PURCHASE_ORDER_SAMPLE;
  const [message, setMessage] = useState<string | null>(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [receiveOpen, setReceiveOpen] = useState(false);

  const totals = useMemo(() => {
    const subtotal = po.items.reduce((sum, item) => sum + item.cost * item.qty, 0);
    const discount = po.discount ?? 0;
    const taxable = Math.max(0, subtotal - discount);
    const tax = taxable * (po.taxRate ?? 0);
    const total = taxable + tax;
    return { subtotal, discount, tax, total };
  }, [po.items, po.discount, po.taxRate]);

  const handlePrint = () => {
    window.print();
  };

  const handleExportPDF = () => {
    setMessage("Se generó la exportación en PDF.");
  };

  const handleCancel = () => {
    setMessage("La orden de compra se marcó como cancelada.");
    setCancelOpen(false);
  };

  const handleQuickReceive = (payload: { qty: number }) => {
    setMessage(`Recepción registrada por ${payload.qty} unidades.`);
    setReceiveOpen(false);
  };

  const closeMessage = () => setMessage(null);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <POHeader
        poNumber={po.number}
        status={po.status}
        onPrint={handlePrint}
        onExportPDF={handleExportPDF}
        onReceive={() => setReceiveOpen(true)}
        onCancel={() => setCancelOpen(true)}
      />

      {message ? (
        <div
          role="status"
          style={{
            padding: 12,
            borderRadius: 12,
            border: "1px solid rgba(14, 165, 233, 0.4)",
            background: "rgba(14, 165, 233, 0.08)",
            color: "#bae6fd",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{message}</span>
          <button onClick={closeMessage} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Cerrar
          </button>
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <POItemsTable items={po.items} />
          <PONotes value={po.note} />
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <POSupplierCard supplier={po.supplier} />
          <POTotalsCard
            subtotal={totals.subtotal}
            discount={totals.discount}
            tax={totals.tax}
            total={totals.total}
          />
          <POReceiptsTimeline items={po.receipts} />
          <POPaymentsTimeline items={po.payments} />
          <POAttachments items={po.attachments} />
          <button
            onClick={() => setReceiveOpen(true)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#22c55e", color: "#0b1220", border: 0, fontWeight: 700 }}
          >
            Registrar recepción
          </button>
          <button
            onClick={() => setCancelOpen(true)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#b91c1c", color: "#fff", border: 0 }}
          >
            Cancelar orden
          </button>
        </div>
      </div>

      <POCancelModal open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={handleCancel} />
      <POReceiveModal open={receiveOpen} onClose={() => setReceiveOpen(false)} onSubmit={handleQuickReceive} />
    </div>
  );
}

export default PurchaseOrderDetailPage;
