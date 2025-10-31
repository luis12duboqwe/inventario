import React, { useMemo, useState } from "react";

import {
  CreditNoteModal,
  PaymentModal,
  PaymentsFiltersBar,
  PaymentsSidePanel,
  PaymentsSummaryCards,
  PaymentsTable,
  RefundModal,
} from "../components/payments";

type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "MIXED";
type TransactionType = "PAYMENT" | "REFUND" | "CREDIT_NOTE";

type TransactionRow = {
  id: string;
  type: TransactionType;
  orderId: string;
  orderNumber?: string;
  customer?: { id: string; name: string };
  method?: PaymentMethod;
  amount: number;
  date: string;
  note?: string;
  status?: "POSTED" | "VOID";
};

type PaymentFilters = {
  query?: string;
  method?: "ALL" | PaymentMethod;
  dateFrom?: string;
  dateTo?: string;
  type?: "ALL" | TransactionType;
};

type ModalState = { open: boolean; orderId?: string } | null;

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function PaymentsCenterPage() {
  const [filters, setFilters] = useState<PaymentFilters>({});
  const [rows] = useState<TransactionRow[]>([]); // TODO(wire): hidratar desde store/servicio
  const [loading] = useState(false); // TODO(wire): enlazar estado de carga
  const [selectedRow, setSelectedRow] = useState<TransactionRow | null>(null);
  const [paymentModal, setPaymentModal] = useState<ModalState>(null);
  const [refundModal, setRefundModal] = useState<ModalState>(null);
  const [creditNoteModal, setCreditNoteModal] = useState<ModalState>(null);

  const summaryItems = useMemo(
    () => [
      { label: "Cobranzas hoy", value: "—" },
      { label: "Mes actual", value: "—" },
      { label: "Pendiente", value: "—" },
      { label: "Reembolsos mes", value: "—" },
    ],
    [],
  );

  const tableRows = useMemo(
    () =>
      rows.map((row) => ({
        id: row.id,
        type: row.type,
        orderNumber: row.orderNumber,
        customer: row.customer?.name,
        method: row.method,
        amount: row.amount,
        date: row.date,
      })),
    [rows],
  );

  const handleOpenPayment = (orderId?: string) => {
    setPaymentModal({ open: true, orderId });
  };

  const handleOpenRefund = (orderId?: string) => {
    setRefundModal({ open: true, orderId });
  };

  const handleOpenCreditNote = (orderId?: string) => {
    setCreditNoteModal({ open: true, orderId });
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <PaymentsSummaryCards items={summaryItems} />
      <PaymentsFiltersBar value={filters} onChange={setFilters} onNewPayment={() => handleOpenPayment()} />
      <PaymentsTable
        rows={tableRows}
        loading={loading}
        onRowClick={(row) => {
          const match = rows.find((item) => item.id === row.id) ?? null;
          setSelectedRow(match);
        }}
      />
      <PaymentsSidePanel
        row={
          selectedRow
            ? {
                ...selectedRow,
                customer: selectedRow.customer?.name,
              }
            : undefined
        }
        onClose={() => setSelectedRow(null)}
        onPay={() => handleOpenPayment(selectedRow?.orderId)}
        onRefund={() => handleOpenRefund(selectedRow?.orderId)}
        onCreditNote={() => handleOpenCreditNote(selectedRow?.orderId)}
      />
      <PaymentModal
        open={Boolean(paymentModal?.open)}
        orderId={paymentModal?.orderId}
        onClose={() => setPaymentModal(null)}
        onSubmit={(payload) => {
          console.debug("Registrar pago", payload, currency.format(payload.amount));
          // TODO(wire): enviar payload al servicio correspondiente
          setPaymentModal(null);
        }}
      />
      <RefundModal
        open={Boolean(refundModal?.open)}
        orderId={refundModal?.orderId}
        onClose={() => setRefundModal(null)}
        onSubmit={(payload) => {
          console.debug("Reembolso", payload, currency.format(payload.amount));
          // TODO(wire): enviar payload al servicio correspondiente
          setRefundModal(null);
        }}
      />
      <CreditNoteModal
        open={Boolean(creditNoteModal?.open)}
        orderId={creditNoteModal?.orderId}
        onClose={() => setCreditNoteModal(null)}
        onSubmit={(payload) => {
          console.debug("Nota de crédito", payload, currency.format(payload.total));
          // TODO(wire): enviar payload al servicio correspondiente
          setCreditNoteModal(null);
        }}
      />
    </div>
  );
}

export default PaymentsCenterPage;
