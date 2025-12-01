import React, { useMemo, useState } from "react";

import {
  OrderActionsBar,
  OrderAttachments,
  OrderCustomerCard,
  OrderHeader,
  OrderItemsTable,
  OrderNotes,
  OrderPaymentsTable,
  OrderShipmentCard,
  OrderTimeline,
  OrderTotalsCard,
} from "../components/order-detail";
import {
  OrdersCancelModal,
  OrdersEmailInvoiceModal,
  OrdersPaymentCaptureModal,
  OrdersReturnModal,
} from "../components/orders";
import {
  CreditNoteModal,
  type CreditNotePayload,
  PaymentModal,
  type PaymentModalPayload,
  RefundModal,
  type RefundModalPayload,
  SettlementCard,
  TransactionsTimeline,
  CustomerDebtCard,
} from "../components/payments";

const ORDER_SAMPLE = {
  id: "ord-1002",
  number: "F-2025-0002",
  status: "OPEN" as const,
  paymentStatus: "PARTIAL" as const,
  customer: {
    name: "Corporativo Atlan",
    phone: "+52 55 2000 2000",
    email: "compras@atlan.mx",
    taxId: "RFC ATL010203XX1",
  },
  items: [
    {
      id: "line-1",
      sku: "APL-IP13P-128",
      name: "iPhone 13 Pro 128GB",
      price: 25999,
      qty: 2,
      discount: 2000,
      subtotal: 25999 * 2 - 2000,
    },
    {
      id: "line-2",
      sku: "SMS-GW6-44",
      name: "Galaxy Watch 6 44mm",
      price: 8999,
      qty: 3,
      subtotal: 8999 * 3,
    },
    {
      id: "line-3",
      sku: "XMI-RN12-128",
      name: "Redmi Note 12 128GB",
      price: 7299,
      qty: 1,
      subtotal: 7299,
    },
  ],
  note: "Cliente corporativo con entrega parcial. Programar envío para sucursal norte.",
  payments: [
    {
      id: "pay-1",
      date: "2025-02-16T11:45:00",
      amount: 30000,
      method: "CARD" as const,
      reference: "TRX-77881",
      note: "Anticipo 50%",
    },
  ],
  shipment: {
    address: "Av. Reforma 100, Piso 12, CDMX",
    company: "DHL Express",
    tracking: "DHL-998877",
  },
  events: [
    { id: "evt-1", date: "2025-02-15T10:15:00", message: "Orden creada desde canal WEB" },
    { id: "evt-2", date: "2025-02-16T11:45:00", message: "Pago parcial registrado" },
  ],
  transactions: [
    {
      id: "txn-1",
      kind: "PAY" as const,
      message: "Pago parcial registrado con tarjeta",
      date: "2025-02-16T11:45:00",
      amount: 30000,
    },
    {
      id: "txn-2",
      kind: "CN" as const,
      message: "Nota de crédito aplicada por diferencia de precio",
      date: "2025-02-17T09:20:00",
      amount: 2500,
    },
  ],
  attachments: [
    { id: "att-1", name: "cotizacion.pdf", url: "#" },
    { id: "att-2", name: "orden_compra.xlsx", url: "#" },
  ],
  taxRate: 0.16,
  paid: 30000,
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function OrderDetailPage() {
  const order = ORDER_SAMPLE;
  const [message, setMessage] = useState<string | null>(null);
  const [emailOpen, setEmailOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [refundOpen, setRefundOpen] = useState(false);
  const [creditNoteOpen, setCreditNoteOpen] = useState(false);

  const totals = useMemo(() => {
    const subtotal = order.items.reduce((sum, item) => sum + item.subtotal, 0);
    const discount = order.items.reduce((sum, item) => sum + (item.discount ?? 0), 0);
    const taxable = Math.max(0, subtotal - discount);
    const taxes = taxable * order.taxRate;
    const total = taxable + taxes;
    const paid = order.paid ?? order.payments.reduce((sum, payment) => sum + payment.amount, 0);
    const balance = Math.max(total - paid, 0);
    return { subtotal, discount, taxes, total, paid, balance };
  }, [order]);

  const handlePrint = () => {
    window.print();
  };

  const handleExportPDF = () => {
    setMessage("Se generó el PDF del pedido.");
  };

  const handleCancel = () => {
    setMessage("La orden se marcó como cancelada.");
    setCancelOpen(false);
  };

  const handleCapturePayment = (payload: { amount: number }) => {
    setMessage(`Pago registrado por ${currency.format(payload.amount)}.`);
    setCaptureOpen(false);
  };

  const handleRegisterReturn = (payload: { amount: number }) => {
    setMessage(`Se procesó una devolución por ${currency.format(payload.amount)}.`);
    setReturnOpen(false);
  };

  const handleSubmitPayment = (payload: PaymentModalPayload) => {
    setMessage(`Pago registrado por ${currency.format(payload.amount)}.`);
    setPaymentOpen(false);
    // TODO(wire): delegar al servicio/store correspondiente
  };

  const handleSubmitRefund = (payload: RefundModalPayload) => {
    setMessage(`Se procesó un reembolso por ${currency.format(payload.amount)}.`);
    setRefundOpen(false);
    // TODO(wire): delegar al servicio/store correspondiente
  };

  const handleSubmitCreditNote = (payload: CreditNotePayload) => {
    setMessage(`Nota de crédito emitida por ${currency.format(payload.total)}.`);
    setCreditNoteOpen(false);
    // TODO(wire): delegar al servicio/store correspondiente
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <OrderHeader
        number={order.number}
        status={order.status}
        paymentStatus={order.paymentStatus}
        onPrint={handlePrint}
        onExportPDF={handleExportPDF}
        onCancel={() => setCancelOpen(true)}
        onMarkPaid={() => setPaymentOpen(true)}
      />

      {message ? (
        <div
          style={{
            padding: 12,
            borderRadius: 12,
            border: "1px solid rgba(34, 197, 94, 0.4)",
            background: "rgba(34, 197, 94, 0.08)",
            color: "#bbf7d0",
          }}
        >
          {message}
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <OrderItemsTable items={order.items} />
          <OrderNotes value={order.note} />
          <TransactionsTimeline items={order.transactions} />
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <OrderCustomerCard customer={order.customer} />
          <CustomerDebtCard totalDebt={120000} creditLimit={250000} />
          <SettlementCard total={totals.total} paid={totals.paid} />
          <OrderTotalsCard
            subtotal={totals.subtotal}
            discount={totals.discount}
            taxes={totals.taxes}
            total={totals.total}
            paid={totals.paid}
            balance={totals.balance}
          />
          <OrderPaymentsTable items={order.payments} />
          <OrderShipmentCard shipment={order.shipment} />
          <OrderTimeline items={order.events} />
          <OrderAttachments items={order.attachments} />
          <button
            onClick={() => setReturnOpen(true)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#f59e0b", color: "#0b1220", border: 0 }}
          >
            Procesar devolución
          </button>
        </div>
      </div>

      <OrderActionsBar
        onPrint={handlePrint}
        onPDF={handleExportPDF}
        onMarkPaid={() => setPaymentOpen(true)}
        onRefund={() => setRefundOpen(true)}
        onCancel={() => setCancelOpen(true)}
      />

      <OrdersEmailInvoiceModal open={emailOpen} onClose={() => setEmailOpen(false)} />
      <OrdersCancelModal open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={handleCancel} />
      <OrdersPaymentCaptureModal open={captureOpen} onClose={() => setCaptureOpen(false)} onSubmit={handleCapturePayment} />
      <OrdersReturnModal open={returnOpen} onClose={() => setReturnOpen(false)} onSubmit={handleRegisterReturn} />
      <PaymentModal open={paymentOpen} orderId={order.id} onClose={() => setPaymentOpen(false)} onSubmit={handleSubmitPayment} />
      <RefundModal open={refundOpen} orderId={order.id} onClose={() => setRefundOpen(false)} onSubmit={handleSubmitRefund} />
      <CreditNoteModal open={creditNoteOpen} orderId={order.id} onClose={() => setCreditNoteOpen(false)} onSubmit={handleSubmitCreditNote} />
    </div>
  );
}

export default OrderDetailPage;
