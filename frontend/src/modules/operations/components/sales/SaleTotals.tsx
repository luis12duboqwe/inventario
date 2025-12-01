import type { SaleSummary } from "./types";

type Props = {
  saleSummary: SaleSummary;
  isSaving: boolean;
  isPrinting: boolean;
  invoiceAvailable: boolean;
  onRequestInvoice: () => void;
  onReset: () => void;
  formatCurrency: (value: number) => string;
};

export function SaleTotals({
  saleSummary,
  isSaving,
  isPrinting,
  invoiceAvailable,
  onRequestInvoice,
  onReset,
  formatCurrency,
}: Props) {
  return (
    <div className="totals-grid">
      <div className="totals-card">
        <h4>Resumen</h4>
        <ul className="compact-list">
          <li>Total bruto: {formatCurrency(saleSummary.gross)}</li>
          <li>Descuento: {formatCurrency(saleSummary.discount)}</li>
          <li>Subtotal: {formatCurrency(saleSummary.subtotal)}</li>
          <li>
            Impuesto ({saleSummary.taxRate.toFixed(2)}%):{" "}
            {formatCurrency(saleSummary.taxAmount)}
          </li>
          <li className="highlight">Total a cobrar: {formatCurrency(saleSummary.total)}</li>
        </ul>
      </div>
      <div className="actions-card">
        <button type="submit" className="btn btn--primary" disabled={isSaving}>
          {isSaving ? "Guardando..." : "Guardar venta"}
        </button>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={onRequestInvoice}
          disabled={!invoiceAvailable || isPrinting}
        >
          {isPrinting ? "Generando factura..." : "Imprimir factura"}
        </button>
        <button type="button" className="btn btn--ghost" onClick={onReset}>
          Limpiar formulario
        </button>
      </div>
    </div>
  );
}
