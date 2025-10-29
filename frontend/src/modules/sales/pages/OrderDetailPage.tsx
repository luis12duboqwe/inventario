import React, { useMemo, useState } from "react";

import {
  OrderCustomerCard,
  OrderHeader,
  OrderItemsTable,
  OrderNotes,
  OrderPaymentsTimeline,
  OrderShipmentCard,
  OrderTotalsCard,
} from "../components/order-detail";
import {
  OrdersCancelModal,
  OrdersEmailInvoiceModal,
  OrdersPaymentCaptureModal,
  OrdersReturnModal,
} from "../components/orders";

const ORDER_SAMPLE = {
  id: "ord-1002",
  number: "F-2025-0002",
  status: "OPEN",
  customer: {
    name: "Corporativo Atlan",
    phone: "+52 55 2000 2000",
    email: "compras@atlan.mx",
    document: "RFC ATL010203XX1",
  },
  items: [
    {
      id: "line-1",
      sku: "APL-IP13P-128",
      name: "iPhone 13 Pro 128GB",
      price: 25999,
      qty: 2,
      discount: 2000,
    },
    {
      id: "line-2",
      sku: "SMS-GW6-44",
      name: "Galaxy Watch 6 44mm",
      price: 8999,
      qty: 3,
    },
    {
      id: "line-3",
      sku: "XMI-RN12-128",
      name: "Redmi Note 12 128GB",
      price: 7299,
      qty: 1,
    },
  ],
  note: "Cliente corporativo con entrega parcial. Programar envío para sucursal norte.",
  payments: [
    {
      id: "pay-1",
      date: "2025-02-16T11:45:00",
      amount: 30000,
      method: "Transferencia",
      note: "Anticipo 50%",
    },
  ],
  shipment: {
    carrier: "DHL Express",
    code: "DHL-998877",
    eta: "2025-02-20",
    address: "Av. Reforma 100, Piso 12, CDMX",
  },
  taxRate: 0.16,
};

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function OrderDetailPage() {
  const order = ORDER_SAMPLE;
  const [message, setMessage] = useState<string | null>(null);
  const [emailOpen, setEmailOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [returnOpen, setReturnOpen] = useState(false);

  const totals = useMemo(() => {
    const subtotal = order.items.reduce((sum, item) => sum + item.price * item.qty, 0);
    const discount = order.items.reduce((sum, item) => sum + (item.discount ?? 0), 0);
    const taxable = Math.max(0, subtotal - discount);
    const tax = taxable * order.taxRate;
    const total = taxable + tax;
    return { subtotal, discount, tax, total };
  }, [order]);

  const handlePrint = () => {
    window.print();
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

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <OrderHeader
        orderNumber={order.number}
        status={order.status}
        onPrint={handlePrint}
        onEmail={() => setEmailOpen(true)}
        onCapturePayment={() => setCaptureOpen(true)}
        onCancel={() => setCancelOpen(true)}
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
        </div>

        <div style={{ display: "grid", gap: 12 }}>
          <OrderCustomerCard customer={order.customer} />
          <OrderTotalsCard
            subtotal={totals.subtotal}
            discount={totals.discount}
            tax={totals.tax}
            total={totals.total}
          />
          <OrderPaymentsTimeline items={order.payments} />
          {order.shipment ? <OrderShipmentCard data={order.shipment} /> : null}
          <button
            onClick={() => setReturnOpen(true)}
            style={{ padding: "8px 12px", borderRadius: 8, background: "#f59e0b", color: "#0b1220", border: 0 }}
          >
            Procesar devolución
          </button>
        </div>
      </div>

      <OrdersEmailInvoiceModal open={emailOpen} onClose={() => setEmailOpen(false)} />
      <OrdersCancelModal open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={handleCancel} />
      <OrdersPaymentCaptureModal open={captureOpen} onClose={() => setCaptureOpen(false)} onSubmit={handleCapturePayment} />
      <OrdersReturnModal open={returnOpen} onClose={() => setReturnOpen(false)} onSubmit={handleRegisterReturn} />
    </div>
  );
}

export default OrderDetailPage;
