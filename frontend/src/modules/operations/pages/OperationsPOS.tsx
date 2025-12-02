import { useCallback, useEffect, useMemo, useState } from "react";

import {
  closePosSession,
  getLastPosSession,
  getPosSaleDetail,
  listPosTaxes,
  openPosSession,
  registerPosReturn,
  submitPosSaleOperation,
  type PosReturnPayload,
  type PosSaleDetailResponse,
  type PosSaleOperationPayload,
  type PosSaleItemRequest,
  type PosSalePaymentEntry,
  type PosSessionSummary,
  type PosTaxInfo,
} from "@api/pos";
import CashPanel from "../components/pos/CashPanel";
import CartTable, { type CartLine } from "../components/pos/CartTable";
import PaymentsPanel, { type PaymentLine } from "../components/pos/PaymentsPanel";
import ReceiptViewer from "../components/pos/ReceiptViewer";
import SalesHistory from "../components/pos/SalesHistory";
import { useOperationsModule } from "../hooks/useOperationsModule";
import { CreditSchedule } from "../components/pos/CreditSchedule";

type StoreSummary = {
  id: number;
  name: string;
};

function createId() {
  return `pos-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

// [PACK34-UI]
export default function OperationsPOS() {
  const { token, stores, selectedStoreId, enablePurchasesSales } = useOperationsModule();

  const storeOptions = useMemo<StoreSummary[]>(() => stores ?? [], [stores]);
  const [activeStoreId, setActiveStoreId] = useState<number | null>(
    selectedStoreId ?? storeOptions[0]?.id ?? null,
  );

  const [session, setSession] = useState<PosSessionSummary | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const [cartItems, setCartItems] = useState<CartLine[]>([]);
  const [payments, setPayments] = useState<PaymentLine[]>([]);
  const [saleNote, setSaleNote] = useState("");
  const [saleReason, setSaleReason] = useState("Venta rápida POS");
  const [saleError, setSaleError] = useState<string | null>(null);
  const [submittingSale, setSubmittingSale] = useState(false);
  const [saleResult, setSaleResult] = useState<PosSaleDetailResponse | null>(null);

  const [historyDetail, setHistoryDetail] = useState<PosSaleDetailResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [taxes, setTaxes] = useState<PosTaxInfo[]>([]);

  useEffect(() => {
    if (!token) return;
    listPosTaxes(token, "Listar impuestos POS")
      .then(setTaxes)
      .catch(() => setTaxes([]));
  }, [token]);

  const refreshSession = useCallback(
    async (storeId: number, reason = "Consultar estado caja") => {
      if (!token) {
        return;
      }
      setSessionLoading(true);
      setSessionError(null);
      try {
        const result = await getLastPosSession(token, storeId, reason);
        setSession(result);
      } catch {
        setSession(null);
        setSessionError("No hay caja abierta en la sucursal seleccionada.");
      } finally {
        setSessionLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    if (activeStoreId) {
      refreshSession(activeStoreId);
    }
  }, [activeStoreId, refreshSession]);

  const subtotal = useMemo(() => {
    return cartItems.reduce((acc, item) => {
      const price = Number(item.price ?? 0);
      return acc + price * (item.qty ?? 1);
    }, 0);
  }, [cartItems]);

  const discountAmount = useMemo(() => {
    return cartItems.reduce((acc, item) => {
      const price = Number(item.price ?? 0);
      const quantity = item.qty ?? 1;
      const discountPercent = Number(item.discount ?? 0);
      return acc + price * quantity * (discountPercent / 100);
    }, 0);
  }, [cartItems]);

  const taxRate = taxes[0]?.rate ?? 0;
  const taxableBase = Math.max(subtotal - discountAmount, 0);
  const taxAmount = (taxableBase * taxRate) / 100;
  const totalDue = taxableBase + taxAmount;

  const handleAddCartItem = (item: Omit<CartLine, "id">) => {
    setCartItems((prev) => [...prev, { id: createId(), ...item }]);
  };

  const handleUpdateCartItem = (
    id: string,
    update: Partial<CartLine>,
    options?: { clear?: ReadonlyArray<keyof CartLine> },
  ) => {
    setCartItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) {
          return item;
        }
        const next: CartLine = { ...item, ...update };
        if (options?.clear?.length) {
          for (const field of options.clear) {
            if (field === "id" || field === "qty") {
              continue;
            }
            delete (next as Record<string, unknown>)[field as string];
          }
        }
        return next;
      }),
    );
  };

  const handleRemoveCartItem = (id: string) => {
    setCartItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleAddPayment = (payment: Omit<PaymentLine, "id">) => {
    setPayments((prev) => [...prev, { id: createId(), ...payment }]);
  };

  const handleUpdatePayment = (id: string, update: Partial<PaymentLine>) => {
    setPayments((prev) =>
      prev.map((payment) => (payment.id === id ? { ...payment, ...update } : payment)),
    );
  };

  const handleRemovePayment = (id: string) => {
    setPayments((prev) => prev.filter((payment) => payment.id !== id));
  };

  const handleSubmitSale = async () => {
    if (!token || !activeStoreId) {
      setSaleError("Selecciona una sucursal con sesión activa.");
      return;
    }
    if (cartItems.length === 0) {
      setSaleError("Agrega al menos un artículo al carrito.");
      return;
    }
    const normalizedPayments: PosSalePaymentEntry[] = (
      payments.length > 0 ? payments : [{ id: createId(), method: "EFECTIVO", amount: totalDue }]
    ).map((entry) => ({ method: entry.method, amount: entry.amount }));

    const items: PosSaleItemRequest[] = cartItems.map((ci) => {
      const item: PosSaleItemRequest = {
        qty: ci.qty ?? 1,
      };
      if (ci.productId != null) {
        item.productId = ci.productId;
      }
      if (ci.device_id != null) {
        item.device_id = ci.device_id;
      }
      const imeiValue = ci.imei?.trim();
      if (imeiValue) {
        item.imei = imeiValue;
      }
      if (ci.price != null && ci.price !== "") {
        item.price = typeof ci.price === "string" ? Number(ci.price) : ci.price;
      }
      if (ci.discount != null) {
        item.discount = ci.discount;
      }
      if (ci.taxCode) {
        item.taxCode = ci.taxCode;
      }
      return item;
    });

    const payload: PosSaleOperationPayload = {
      branchId: activeStoreId,
      confirm: true,
      items,
      payments: normalizedPayments,
    };

    if (session?.session_id != null) {
      payload.sessionId = session.session_id;
    }

    const trimmedNote = saleNote.trim();
    if (trimmedNote) {
      payload.note = trimmedNote;
    }

    setSubmittingSale(true);
    setSaleError(null);
    try {
      const response = await submitPosSaleOperation(token, payload, saleReason);
      if (response.sale) {
        const detail: PosSaleDetailResponse = {
          sale: response.sale,
          receipt_url: response.receipt_url ?? `/pos/receipt/${response.sale.id}`,
        };
        if (response.receipt_pdf_base64 != null) {
          detail.receipt_pdf_base64 = response.receipt_pdf_base64;
        }
        if (response.debt_summary) {
          detail.debt_summary = response.debt_summary;
        }
        detail.credit_schedule = response.credit_schedule ?? [];
        if (response.debt_receipt_pdf_base64 != null) {
          detail.debt_receipt_pdf_base64 = response.debt_receipt_pdf_base64;
        }
        if (response.payment_receipts) {
          detail.payment_receipts = response.payment_receipts;
        }
        setSaleResult(detail);
      }
      setCartItems([]);
      setPayments([]);
      setSaleNote("");
      await refreshSession(activeStoreId, "Actualizar caja tras venta");
    } catch {
      setSaleError("No fue posible registrar la venta. Verifica los datos y la sesión de caja.");
    } finally {
      setSubmittingSale(false);
    }
  };

  const handleOpenSession = async ({
    amount,
    notes,
    reason,
  }: {
    amount: number;
    notes: string;
    reason: string;
  }) => {
    if (!token || !activeStoreId) return;
    await openPosSession(token, { branchId: activeStoreId, openingAmount: amount, notes }, reason);
    await refreshSession(activeStoreId, "Apertura de caja");
  };

  const handleCloseSession = async ({
    amount,
    notes,
    reason,
  }: {
    amount: number;
    notes: string;
    reason: string;
  }) => {
    if (!token || !session) return;
    await closePosSession(
      token,
      {
        sessionId: session.session_id,
        closingAmount: amount,
        notes,
        payments: { EFECTIVO: amount },
      },
      reason,
    );
    await refreshSession(session.branch_id, "Cierre de caja");
  };

  const handleSearchSale = async (saleId: number, reason: string) => {
    if (!token) return;
    setHistoryLoading(true);
    try {
      const detail = await getPosSaleDetail(token, saleId, reason);
      setHistoryDetail(detail);
    } catch {
      setHistoryDetail(null);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleRegisterReturn = async (payload: PosReturnPayload, reason: string) => {
    if (!token) return;
    await registerPosReturn(token, payload, reason);
    const refreshStoreId = activeStoreId ?? session?.branch_id ?? null;
    if (refreshStoreId) {
      await refreshSession(refreshStoreId, "Actualizar caja tras devolución");
    }
  };

  if (!enablePurchasesSales) {
    return (
      <div className="operations-pos-disabled">
        <h2>POS / Caja</h2>
        <p className="muted-text">
          Activa el flag corporativo <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code> para utilizar el
          punto de venta.
        </p>
      </div>
    );
  }

  return (
    <div className="pos-page">
      <header className="pos-page__intro">
        <div>
          <h2>POS / Caja</h2>
          <p className="muted-text">
            Gestiona la caja diaria, captura ventas con impuestos y genera devoluciones sin salir de
            la misma pantalla.
          </p>
        </div>
      </header>

      <div className="pos-layout">
        <div className="pos-layout__column">
          <CashPanel
            stores={storeOptions}
            selectedStoreId={activeStoreId}
            onStoreChange={(id) => {
              setActiveStoreId(id);
              setSaleResult(null);
              setHistoryDetail(null);
            }}
            session={session}
            onOpenSession={handleOpenSession}
            onCloseSession={handleCloseSession}
            refreshing={sessionLoading}
            onRefresh={() =>
              activeStoreId && refreshSession(activeStoreId, "Actualizar caja manual")
            }
            error={sessionError}
          />

          <CartTable
            items={cartItems}
            onAdd={handleAddCartItem}
            onUpdate={handleUpdateCartItem}
            onRemove={handleRemoveCartItem}
          />

          <section className="card">
            <header className="card__header">
              <h3 className="card__title">Totales</h3>
            </header>
            <dl className="pos-totals">
              <div>
                <dt>Subtotal</dt>
                <dd>${subtotal.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Descuentos</dt>
                <dd>${discountAmount.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Impuestos ({taxRate.toFixed(2)}%)</dt>
                <dd>${taxAmount.toFixed(2)}</dd>
              </div>
              <div>
                <dt>Total a cobrar</dt>
                <dd className="pos-totals__highlight">${totalDue.toFixed(2)}</dd>
              </div>
            </dl>
            <label className="pos-note-field">
              <span>Notas de la venta</span>
              <textarea
                value={saleNote}
                onChange={(event) => setSaleNote(event.target.value)}
                rows={2}
              />
            </label>
            <label className="pos-note-field">
              <span>Motivo corporativo</span>
              <input
                type="text"
                minLength={5}
                value={saleReason}
                onChange={(event) => setSaleReason(event.target.value)}
                required
              />
            </label>
            {saleError ? <p className="alert error">{saleError}</p> : null}
            <button
              type="button"
              className="btn btn--primary"
              onClick={handleSubmitSale}
              disabled={submittingSale}
            >
              {submittingSale ? "Registrando…" : "Confirmar venta"}
            </button>
          </section>

          <PaymentsPanel
            payments={payments}
            onAdd={handleAddPayment}
            onUpdate={handleUpdatePayment}
            onRemove={handleRemovePayment}
            totalDue={totalDue}
          />
        </div>

        <div className="pos-layout__column">
          <ReceiptViewer
            saleId={saleResult?.sale.id ?? null}
            receiptUrl={saleResult?.receipt_url ?? null}
            {...(saleResult?.receipt_pdf_base64 != null
              ? { receiptPdfBase64: saleResult.receipt_pdf_base64 }
              : {})}
          />
          <CreditSchedule
            debtSummary={saleResult?.debt_summary ?? null}
            schedule={saleResult?.credit_schedule ?? []}
            debtReceiptBase64={saleResult?.debt_receipt_pdf_base64 ?? null}
            paymentReceipts={saleResult?.payment_receipts ?? []}
          />
          <SalesHistory
            loading={historyLoading}
            saleDetail={historyDetail}
            onSearch={handleSearchSale}
            onReturn={handleRegisterReturn}
          />
        </div>
      </div>
    </div>
  );
}
