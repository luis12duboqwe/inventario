import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  CreditNoteModal,
  type CreditNotePayload,
  PaymentModal,
  type PaymentModalPayload,
  PaymentsFiltersBar,
  PaymentsSidePanel,
  PaymentsSummaryCards,
  PaymentsTable,
  RefundModal,
  type RefundModalPayload,
} from "../components/payments";
import {
  getPaymentCenter,
  registerPaymentCenterCreditNote,
  registerPaymentCenterPayment,
  registerPaymentCenterRefund,
  type PaymentCenterResponse,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "MIXED";
type TransactionType = "PAYMENT" | "REFUND" | "CREDIT_NOTE";

type TransactionRow = {
  id: string;
  type: TransactionType;
  orderId?: string;
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

type ModalState = { open: boolean; orderId?: string; row?: TransactionRow | null } | null;

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function PaymentsCenterPage() {
  const { token, pushToast } = useDashboard();
  const [filters, setFilters] = useState<PaymentFilters>({});
  const [rows, setRows] = useState<TransactionRow[]>([]);
  const [summary, setSummary] = useState<PaymentCenterResponse["summary"] | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedRow, setSelectedRow] = useState<TransactionRow | null>(null);
  const [paymentModal, setPaymentModal] = useState<ModalState>(null);
  const [refundModal, setRefundModal] = useState<ModalState>(null);
  const [creditNoteModal, setCreditNoteModal] = useState<ModalState>(null);

  const loadPayments = useCallback(async () => {
    if (!token) {
      return;
    }
    setLoading(true);
    try {
      const response = await getPaymentCenter(token, {
        limit: 100,
        query: filters.query?.trim() || undefined,
        method: filters.method && filters.method !== "ALL" ? filters.method : undefined,
        type: filters.type && filters.type !== "ALL" ? filters.type : undefined,
        dateFrom: filters.dateFrom,
        dateTo: filters.dateTo,
      });
      setSummary(response.summary);
      const mapped: TransactionRow[] = response.transactions.map((transaction) => ({
        id: String(transaction.id),
        type: transaction.type,
        orderId: transaction.order_id ? String(transaction.order_id) : undefined,
        orderNumber: transaction.order_number ?? undefined,
        customer: {
          id: String(transaction.customer_id),
          name: transaction.customer_name,
        },
        method: (transaction.method as PaymentMethod | undefined) ?? undefined,
        amount: transaction.amount,
        date: transaction.created_at,
        note: transaction.note ?? undefined,
        status: transaction.status,
      }));
      setRows(mapped);
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible cargar el centro de pagos";
      pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [filters.dateFrom, filters.dateTo, filters.method, filters.query, filters.type, pushToast, token]);

  useEffect(() => {
    void loadPayments();
  }, [loadPayments]);

  const summaryItems = useMemo(() => {
    if (!summary) {
      return [
        { label: "Cobranzas hoy", value: "—" },
        { label: "Mes actual", value: "—" },
        { label: "Pendiente", value: "—" },
        { label: "Reembolsos mes", value: "—" },
      ];
    }
    return [
      { label: "Cobranzas hoy", value: currency.format(summary.collections_today) },
      { label: "Mes actual", value: currency.format(summary.collections_month) },
      { label: "Pendiente", value: currency.format(summary.pending_balance) },
      { label: "Reembolsos mes", value: currency.format(summary.refunds_month) },
    ];
  }, [summary]);

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
    if (!selectedRow && !orderId) {
      pushToast({ message: "Selecciona un movimiento para registrar el cobro.", variant: "error" });
      return;
    }
    setPaymentModal({ open: true, orderId, row: selectedRow });
  };

  const handleOpenRefund = (orderId?: string) => {
    if (!selectedRow && !orderId) {
      pushToast({ message: "Selecciona un movimiento para registrar el reembolso.", variant: "error" });
      return;
    }
    setRefundModal({ open: true, orderId, row: selectedRow });
  };

  const handleOpenCreditNote = (orderId?: string) => {
    if (!selectedRow && !orderId) {
      pushToast({ message: "Selecciona un movimiento para emitir la nota de crédito.", variant: "error" });
      return;
    }
    setCreditNoteModal({ open: true, orderId, row: selectedRow });
  };

  const resolveCustomer = (row?: TransactionRow | null) => {
    if (!row?.customer?.id) {
      return null;
    }
    const customerId = Number(row.customer.id);
    if (Number.isNaN(customerId)) {
      return null;
    }
    return { id: customerId, name: row.customer.name };
  };

  const extractSaleId = (orderId?: string) => {
    if (!orderId) {
      return undefined;
    }
    const numeric = Number(orderId);
    return Number.isNaN(numeric) ? undefined : numeric;
  };

  const handlePaymentSubmit = async (payload: PaymentModalPayload) => {
    if (!token) {
      return;
    }
    const contextRow = paymentModal?.row ?? selectedRow;
    const customer = resolveCustomer(contextRow);
    if (!customer) {
      pushToast({ message: "No fue posible determinar el cliente para el cobro.", variant: "error" });
      return;
    }
    const reason = payload.reason?.trim() ?? "";
    if (reason.length < 5) {
      pushToast({ message: "Ingresa un motivo corporativo de al menos 5 caracteres.", variant: "error" });
      return;
    }
    try {
      await registerPaymentCenterPayment(
        token,
        {
          customer_id: customer.id,
          amount: payload.amount,
          method: payload.method,
          reference: payload.reference,
          sale_id: extractSaleId(payload.orderId ?? contextRow?.orderId),
        },
        reason,
      );
      pushToast({
        message: `Pago registrado por ${currency.format(payload.amount)}.`,
        variant: "success",
      });
      setPaymentModal(null);
      await loadPayments();
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible registrar el pago";
      pushToast({ message, variant: "error" });
    }
  };

  const handleRefundSubmit = async (payload: RefundModalPayload) => {
    if (!token) {
      return;
    }
    const contextRow = refundModal?.row ?? selectedRow;
    const customer = resolveCustomer(contextRow);
    if (!customer) {
      pushToast({ message: "Selecciona un movimiento válido para reembolsar.", variant: "error" });
      return;
    }
    const reason = payload.notes?.trim() ?? "";
    if (reason.length < 5) {
      pushToast({ message: "El motivo corporativo debe tener al menos 5 caracteres.", variant: "error" });
      return;
    }
    try {
      await registerPaymentCenterRefund(
        token,
        {
          customer_id: customer.id,
          amount: payload.amount,
          method: payload.method,
          reason: payload.reason,
          note: reason,
          sale_id: extractSaleId(payload.orderId ?? contextRow?.orderId),
        },
        reason,
      );
      pushToast({
        message: `Reembolso registrado por ${currency.format(payload.amount)}.`,
        variant: "success",
      });
      setRefundModal(null);
      await loadPayments();
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible registrar el reembolso";
      pushToast({ message, variant: "error" });
    }
  };

  const handleCreditNoteSubmit = async (payload: CreditNotePayload) => {
    if (!token) {
      return;
    }
    const contextRow = creditNoteModal?.row ?? selectedRow;
    const customer = resolveCustomer(contextRow);
    if (!customer) {
      pushToast({ message: "Selecciona un movimiento válido para emitir la nota de crédito.", variant: "error" });
      return;
    }
    const reason = payload.reason?.trim() ?? "";
    if (reason.length < 5) {
      pushToast({ message: "El motivo corporativo debe tener al menos 5 caracteres.", variant: "error" });
      return;
    }
    try {
      await registerPaymentCenterCreditNote(
        token,
        {
          customer_id: customer.id,
          total: payload.total,
          lines: payload.lines.map((line) => ({
            description: line.name || "Concepto",
            quantity: line.qty,
            amount: line.amount,
          })),
          note: reason,
          sale_id: extractSaleId(payload.orderId ?? contextRow?.orderId),
        },
        reason,
      );
      pushToast({
        message: `Nota de crédito emitida por ${currency.format(payload.total)}.`,
        variant: "success",
      });
      setCreditNoteModal(null);
      await loadPayments();
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible emitir la nota de crédito";
      pushToast({ message, variant: "error" });
    }
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <PaymentsSummaryCards items={summaryItems} loading={loading && rows.length === 0} />
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
        onSubmit={handlePaymentSubmit}
      />
      <RefundModal
        open={Boolean(refundModal?.open)}
        orderId={refundModal?.orderId}
        onClose={() => setRefundModal(null)}
        onSubmit={handleRefundSubmit}
      />
      <CreditNoteModal
        open={Boolean(creditNoteModal?.open)}
        orderId={creditNoteModal?.orderId}
        onClose={() => setCreditNoteModal(null)}
        onSubmit={handleCreditNoteSubmit}
      />
    </div>
  );
}

export default PaymentsCenterPage;
