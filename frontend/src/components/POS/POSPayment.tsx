import { useMemo } from "react";
import type { PaymentMethod } from "../../api";

type Totals = {
  subtotal: number;
  tax: number;
  total: number;
};

type Props = {
  paymentMethod: PaymentMethod;
  onPaymentMethodChange: (method: PaymentMethod) => void;
  customerName: string;
  onCustomerNameChange: (value: string) => void;
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
  totals: Totals;
  disabled: boolean;
  loading: boolean;
  onSubmit: (mode: "draft" | "sale") => Promise<void>;
  warnings: string[];
};

const paymentLabels: Record<PaymentMethod, string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  OTRO: "Otro",
  CREDITO: "Crédito",
};

function POSPayment({
  paymentMethod,
  onPaymentMethodChange,
  customerName,
  onCustomerNameChange,
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
  totals,
  disabled,
  loading,
  onSubmit,
  warnings,
}: Props) {
  const canSubmit = useMemo(() => {
    return !disabled && reason.trim().length >= 5 && confirmChecked;
  }, [disabled, reason, confirmChecked]);

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
      <div className="form-grid">
        <label>
          Método de pago
          <select value={paymentMethod} onChange={(event) => onPaymentMethodChange(event.target.value as PaymentMethod)}>
            {Object.entries(paymentLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Cliente (opcional)
          <input value={customerName} onChange={(event) => onCustomerNameChange(event.target.value)} placeholder="Nombre del cliente" />
        </label>
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
          className="button ghost"
          onClick={() => onSubmit("draft")}
          disabled={disabled || loading}
        >
          Guardar borrador
        </button>
        <button
          type="button"
          className="button primary"
          onClick={() => onSubmit("sale")}
          disabled={!canSubmit || loading}
        >
          {loading ? "Registrando..." : "Registrar venta"}
        </button>
      </div>
    </section>
  );
}

export default POSPayment;
