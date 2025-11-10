import { useMemo } from "react";
import type { CashSession, Customer, PaymentMethod } from "../../../api";

type Totals = {
  subtotal: number;
  tax: number;
  total: number;
};

type Props = {
  paymentMethod: PaymentMethod;
  onPaymentMethodChange: (method: PaymentMethod) => void;
  customerId: number | null;
  customerName: string;
  onCustomerNameChange: (value: string) => void;
  customerOptions: Customer[];
  customerSearch: string;
  onCustomerSearchChange: (value: string) => void;
  onCustomerSelect: (customerId: number | null) => void;
  onQuickCreateCustomer: () => void;
  selectedCustomer: Customer | null;
  customerLoading: boolean;
  notes: string;
  onNotesChange: (value: string) => void;
  globalDiscount: number;
  onGlobalDiscountChange: (value: number) => void;
  applyTaxes: boolean;
  onToggleTaxes: (value: boolean) => void;
  reason: string;
  onReasonChange: (value: string) => void;
  confirmChecked: boolean;
  onConfirmChange: (value: boolean) => void;
  cashSessionId: number | null;
  cashSessions: CashSession[];
  onCashSessionChange: (sessionId: number | null) => void;
  onOpenCashSession: () => void;
  onCloseCashSession: () => void;
  cashLoading: boolean;
  paymentBreakdown: Record<PaymentMethod, number>;
  onPaymentBreakdownChange: (method: PaymentMethod, value: number) => void;
  onAutoDistributeBreakdown: () => void;
  onResetBreakdown: () => void;
  activeCashSessionId: number | null;
  totals: Totals;
  disabled: boolean;
  loading: boolean;
  onSubmit: (mode: "draft" | "sale") => Promise<void>;
  warnings: string[];
};

export type PaymentModalProps = Props;

const paymentLabels: Record<PaymentMethod, string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  OTRO: "Otro",
  CREDITO: "Crédito",
  NOTA_CREDITO: "Nota de crédito",
};

const paymentMethodsOrder: PaymentMethod[] = [
  "EFECTIVO",
  "TARJETA",
  "TRANSFERENCIA",
  "CREDITO",
  "NOTA_CREDITO",
  "OTRO",
];

function PaymentModal({
  paymentMethod,
  onPaymentMethodChange,
  customerId,
  customerName,
  onCustomerNameChange,
  customerOptions,
  customerSearch,
  onCustomerSearchChange,
  onCustomerSelect,
  onQuickCreateCustomer,
  selectedCustomer,
  customerLoading,
  notes,
  onNotesChange,
  globalDiscount,
  onGlobalDiscountChange,
  applyTaxes,
  onToggleTaxes,
  reason,
  onReasonChange,
  confirmChecked,
  onConfirmChange,
  cashSessionId,
  cashSessions,
  onCashSessionChange,
  onOpenCashSession,
  onCloseCashSession,
  cashLoading,
  paymentBreakdown,
  onPaymentBreakdownChange,
  onAutoDistributeBreakdown,
  onResetBreakdown,
  activeCashSessionId,
  totals,
  disabled,
  loading,
  onSubmit,
  warnings,
}: Props) {
  const requiresCustomer = paymentMethod === "CREDITO";
  const canSubmit = useMemo(() => {
    return (
      !disabled &&
      reason.trim().length >= 5 &&
      confirmChecked &&
      (!requiresCustomer || Boolean(customerId))
    );
  }, [disabled, reason, confirmChecked, requiresCustomer, customerId]);

  const breakdownTotal = useMemo(
    () =>
      paymentMethodsOrder.reduce(
        (acc, method) => acc + Number(paymentBreakdown[method] ?? 0),
        0
      ),
    [paymentBreakdown]
  );

  const breakdownDifference = Number((totals.total - breakdownTotal).toFixed(2));
  const breakdownMatches = Math.abs(breakdownDifference) <= 0.5;

  const formatCurrency = (value: number) => value.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  return (
    <section className="card">
      <h3>Pago y confirmación</h3>
      <p className="card-subtitle">Verifica totales, motivo corporativo y confirma visualmente la venta.</p>
      {warnings.length > 0 ? (
        <ul className="alert warning">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
      {requiresCustomer && !customerId ? (
        <div className="alert warning">
          Selecciona un cliente registrado para habilitar ventas a crédito corporativo.
        </div>
      ) : null}
      <div className="form-grid">
        <label>
          Método de pago
          <select value={paymentMethod} onChange={(event) => onPaymentMethodChange(event.target.value as PaymentMethod)}>
            {paymentMethodsOrder.map((method) => (
              <option key={method} value={method}>
                {paymentLabels[method]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sesión de caja
          <select
            value={cashSessionId ?? ""}
            onChange={(event) =>
              onCashSessionChange(event.target.value ? Number(event.target.value) : null)
            }
            disabled={cashLoading || cashSessions.length === 0}
          >
            <option value="">Sin asignar</option>
            {cashSessions.map((session) => (
              <option key={session.id} value={session.id}>
                #{session.id} · {session.status === "ABIERTO" ? "Abierta" : "Cerrada"}
              </option>
            ))}
          </select>
          <span className="muted-text">
            {cashLoading
              ? "Consultando historial de caja..."
              : activeCashSessionId
              ? `Sesión abierta #${activeCashSessionId}`
              : "Puedes asignar la venta a una sesión cerrada o abrir una nueva."}
          </span>
        </label>
        <label>
          Buscar cliente
          <input
            value={customerSearch}
            onChange={(event) => onCustomerSearchChange(event.target.value)}
            placeholder="Nombre, correo o nota"
            disabled={customerLoading}
          />
          <span className="muted-text">Escribe al menos 2 caracteres para refinar la búsqueda.</span>
        </label>
        <label>
          Cliente registrado
          <select
            value={customerId ?? ""}
            onChange={(event) =>
              onCustomerSelect(event.target.value ? Number(event.target.value) : null)
            }
            disabled={customerLoading}
          >
            <option value="">Mostrador sin registro</option>
            {customerOptions.map((customer) => (
              <option key={customer.id} value={customer.id}>
                {customer.name} · Deuda ${formatCurrency(customer.outstanding_debt)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cliente manual (opcional)
          <input
            value={customerName}
            onChange={(event) => onCustomerNameChange(event.target.value)}
            placeholder="Nombre libre para el ticket"
          />
        </label>
        <div className="wide actions-row">
          <button type="button" className="btn btn--ghost" onClick={onQuickCreateCustomer}>
            Alta rápida de cliente
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onOpenCashSession}
            disabled={cashLoading}
          >
            Abrir caja
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onCloseCashSession}
            disabled={cashLoading || !activeCashSessionId}
          >
            Cerrar caja
          </button>
        </div>
        <label>
          Descuento global (%)
          <input
            type="number"
            min={0}
            max={100}
            value={globalDiscount}
            onChange={(event) => onGlobalDiscountChange(Math.min(100, Math.max(0, Number(event.target.value))))}
          />
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={applyTaxes} onChange={(event) => onToggleTaxes(event.target.checked)} /> Aplicar impuestos configurados
        </label>
        <label className="wide">
          Notas (opcional)
          <textarea value={notes} onChange={(event) => onNotesChange(event.target.value)} rows={2} placeholder="Observaciones del cliente o entrega" />
        </label>
        <label className="wide">
          Motivo corporativo
          <input value={reason} onChange={(event) => onReasonChange(event.target.value)} placeholder="Ej. Venta mostrador sucursal centro" />
          <span className="muted-text">Obligatorio · mínimo 5 caracteres.</span>
        </label>
        <label className="checkbox wide">
          <input type="checkbox" checked={confirmChecked} onChange={(event) => onConfirmChange(event.target.checked)} />
          Confirmo que el total coincide con lo mostrado al cliente.
        </label>
      </div>
      {selectedCustomer ? (
        <div className="muted-text">
          <strong>{selectedCustomer.name}</strong> · Deuda actual ${formatCurrency(selectedCustomer.outstanding_debt)}
        </div>
      ) : null}
      <h4>Desglose de pago</h4>
      <div className="form-grid">
        {paymentMethodsOrder.map((method) => (
          <label key={method}>
            {paymentLabels[method]}
            <input
              type="number"
              min={0}
              step="0.01"
              value={Number(paymentBreakdown[method] ?? 0)}
              onChange={(event) => onPaymentBreakdownChange(method, Number(event.target.value))}
            />
          </label>
        ))}
      </div>
      <div className="actions-row">
        <button type="button" className="btn btn--ghost" onClick={onAutoDistributeBreakdown}>
          Aplicar total al método seleccionado
        </button>
        <button type="button" className="btn btn--ghost" onClick={onResetBreakdown}>
          Limpiar desglose
        </button>
      </div>
      {totals.total > 0 ? (
        breakdownMatches ? (
          <p className="muted-text">El desglose coincide con el total a cobrar.</p>
        ) : (
          <div className="alert warning">
            Ajusta ${formatCurrency(Math.abs(breakdownDifference))} para conciliar el total a cobrar.
          </div>
        )
      ) : null}
      <div className="totals-panel">
        <div>
          <span className="muted-text">Subtotal</span>
          <strong>${formatCurrency(totals.subtotal)}</strong>
        </div>
        <div>
          <span className="muted-text">Impuestos</span>
          <strong>${formatCurrency(totals.tax)}</strong>
        </div>
        <div>
          <span className="muted-text">Total a cobrar</span>
          <strong className="highlight">${formatCurrency(totals.total)}</strong>
        </div>
      </div>
      <div className="actions-row">
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => onSubmit("draft")}
          disabled={disabled || loading}
        >
          Guardar borrador
        </button>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => onSubmit("sale")}
          disabled={!canSubmit || loading}
        >
          {loading ? "Registrando..." : "Registrar venta"}
        </button>
      </div>
    </section>
  );
}

export default PaymentModal;
