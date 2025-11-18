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
  type PaymentFilters,
  type PaymentMethod as UiPaymentMethod,
  type PaymentRow,
  type PaymentRowDetails,
} from "../components/payments";
import {
  getPaymentCenter,
  registerPaymentCenterCreditNote,
  registerPaymentCenterPayment,
  registerPaymentCenterRefund,
  type PaymentCenterCreditNoteInput,
  type PaymentCenterPaymentInput,
  type PaymentCenterRefundInput,
  type PaymentCenterResponse,
  type PaymentMethod as ApiPaymentMethod,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

type TransactionType = "PAYMENT" | "REFUND" | "CREDIT_NOTE";

const METHOD_UI_TO_API: Record<UiPaymentMethod, ApiPaymentMethod> = {
  CASH: "EFECTIVO",
  CARD: "TARJETA",
  TRANSFER: "TRANSFERENCIA",
  MIXED: "OTRO",
};

const METHOD_API_TO_UI: Record<ApiPaymentMethod, UiPaymentMethod> = {
  EFECTIVO: "CASH",
  TARJETA: "CARD",
  TRANSFERENCIA: "TRANSFER",
  OTRO: "MIXED",
  CREDITO: "MIXED",
};

const METHOD_LABELS: Record<UiPaymentMethod, string> = {
  CASH: "Efectivo",
  CARD: "Tarjeta",
  TRANSFER: "Transferencia",
  MIXED: "Mixto",
};

type TransactionRow = {
  id: string;
  type: TransactionType;
  orderId?: string;
  orderNumber?: string;
  customer?: { id: string; name: string };
  method?: UiPaymentMethod;
  amount: number;
  date: string;
  note?: string;
  status?: "POSTED" | "VOID";
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
      const requestFilters: NonNullable<Parameters<typeof getPaymentCenter>[1]> = {
        limit: 100,
      };
      const trimmedQuery = filters.query?.trim();
      if (trimmedQuery) {
        requestFilters.query = trimmedQuery;
      }
      if (filters.dateFrom) {
        requestFilters.dateFrom = filters.dateFrom;
      }
      if (filters.dateTo) {
        requestFilters.dateTo = filters.dateTo;
      }
      const methodFilter = filters.method;
      if (methodFilter && methodFilter !== "ALL") {
        requestFilters.method = METHOD_UI_TO_API[methodFilter];
      }
      if (filters.type && filters.type !== "ALL") {
        requestFilters.type = filters.type;
      }
      const response = await getPaymentCenter(token, requestFilters);
      setSummary(response.summary);
      const mapped: TransactionRow[] = response.transactions.map((transaction) => {
        const row: TransactionRow = {
          id: String(transaction.id),
          type: transaction.type,
          amount: transaction.amount,
          date: transaction.created_at,
        };
        if (transaction.order_id != null) {
          row.orderId = String(transaction.order_id);
        }
        if (transaction.order_number) {
          row.orderNumber = transaction.order_number;
        }
        if (transaction.customer_id != null && transaction.customer_name) {
          row.customer = {
            id: String(transaction.customer_id),
            name: transaction.customer_name,
          };
        }
        if (transaction.method) {
            const apiMethod = transaction.method as ApiPaymentMethod;
            const mappedMethod = METHOD_API_TO_UI[apiMethod];
            if (mappedMethod) {
              row.method = mappedMethod;
            }
        }
        if (transaction.note) {
          row.note = transaction.note;
        }
        if (transaction.status) {
          row.status = transaction.status;
        }
        return row;
      });
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

  const tableRows = useMemo(() => {
    return rows.map((row) => {
      const entry: PaymentRow = {
        id: row.id,
        type: row.type,
        amount: row.amount,
        date: row.date,
      };
      if (row.orderNumber) {
        entry.orderNumber = row.orderNumber;
      }
      if (row.customer?.name) {
        entry.customer = row.customer.name;
      }
      if (row.method) {
        entry.method = METHOD_LABELS[row.method];
      }
      return entry;
    });
  }, [rows]);

  const handleOpenPayment = (orderId?: string) => {
    if (!selectedRow && !orderId) {
      pushToast({ message: "Selecciona un movimiento para registrar el cobro.", variant: "error" });
      return;
    }
    const nextModal: Exclude<ModalState, null> = { open: true };
    if (orderId) {
      nextModal.orderId = orderId;
    }
    if (selectedRow) {
      nextModal.row = selectedRow;
    }
    setPaymentModal(nextModal);
  };

  const handleOpenRefund = (orderId?: string) => {
    if (!selectedRow && !orderId) {
      pushToast({ message: "Selecciona un movimiento para registrar el reembolso.", variant: "error" });
      return;
    }
    const nextModal: Exclude<ModalState, null> = { open: true };
    if (orderId) {
      nextModal.orderId = orderId;
    }
    if (selectedRow) {
      nextModal.row = selectedRow;
    }
    setRefundModal(nextModal);
  };

  const handleOpenCreditNote = (orderId?: string) => {
    if (!selectedRow && !orderId) {
      pushToast({ message: "Selecciona un movimiento para emitir la nota de crédito.", variant: "error" });
      return;
    }
    const nextModal: Exclude<ModalState, null> = { open: true };
    if (orderId) {
      nextModal.orderId = orderId;
    }
    if (selectedRow) {
      nextModal.row = selectedRow;
    }
    setCreditNoteModal(nextModal);
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
      const saleId = extractSaleId(payload.orderId ?? contextRow?.orderId);
      const request: PaymentCenterPaymentInput = {
        customer_id: customer.id,
        amount: payload.amount,
        method: METHOD_UI_TO_API[payload.method],
      };
      if (payload.reference) {
        request.reference = payload.reference;
      }
      if (typeof saleId === "number") {
        request.sale_id = saleId;
      }
      await registerPaymentCenterPayment(token, request, reason);
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
      const saleId = extractSaleId(payload.orderId ?? contextRow?.orderId);
      const request: PaymentCenterRefundInput = {
        customer_id: customer.id,
        amount: payload.amount,
        method: METHOD_UI_TO_API[payload.method],
        reason: payload.reason,
        note: reason,
      };
      if (typeof saleId === "number") {
        request.sale_id = saleId;
      }
      await registerPaymentCenterRefund(token, request, reason);
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
      const saleId = extractSaleId(payload.orderId ?? contextRow?.orderId);
      const request: PaymentCenterCreditNoteInput = {
        customer_id: customer.id,
        total: payload.total,
        lines: payload.lines.map((line) => ({
          description: line.name || "Concepto",
          quantity: line.qty,
          amount: line.amount,
        })),
        note: reason,
      };
      if (typeof saleId === "number") {
        request.sale_id = saleId;
      }
      await registerPaymentCenterCreditNote(token, request, reason);
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
        row={selectedRow ? (() => {
          const detail: PaymentRowDetails = {
            id: selectedRow.id,
            type: selectedRow.type,
            amount: selectedRow.amount,
            date: selectedRow.date,
          };
          if (selectedRow.orderId) {
            detail.orderId = selectedRow.orderId;
          }
          if (selectedRow.orderNumber) {
            detail.orderNumber = selectedRow.orderNumber;
          }
          const customerName = selectedRow.customer?.name;
          if (customerName) {
            detail.customer = customerName;
          }
          if (selectedRow.method) {
            detail.method = METHOD_LABELS[selectedRow.method];
          }
          if (selectedRow.note) {
            detail.note = selectedRow.note;
          }
          return detail;
        })() : null}
        onClose={() => setSelectedRow(null)}
        onPay={() => handleOpenPayment(selectedRow?.orderId)}
        onRefund={() => handleOpenRefund(selectedRow?.orderId)}
        onCreditNote={() => handleOpenCreditNote(selectedRow?.orderId)}
      />
      <PaymentModal
        open={Boolean(paymentModal?.open)}
        {...(paymentModal?.orderId ? { orderId: paymentModal.orderId } : {})}
        onClose={() => setPaymentModal(null)}
        onSubmit={handlePaymentSubmit}
      />
      <RefundModal
        open={Boolean(refundModal?.open)}
        {...(refundModal?.orderId ? { orderId: refundModal.orderId } : {})}
        onClose={() => setRefundModal(null)}
        onSubmit={handleRefundSubmit}
      />
      <CreditNoteModal
        open={Boolean(creditNoteModal?.open)}
        {...(creditNoteModal?.orderId ? { orderId: creditNoteModal.orderId } : {})}
        onClose={() => setCreditNoteModal(null)}
        onSubmit={handleCreditNoteSubmit}
      />
    </div>
  );
}

export default PaymentsCenterPage;
