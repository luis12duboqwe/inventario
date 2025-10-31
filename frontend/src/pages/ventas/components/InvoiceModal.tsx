import Modal from "../../../shared/components/ui/Modal";

import type { SaleSummary, SaleLine } from "./types";

const formatListCurrency = (value: number) =>
  value.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

type Props = {
  open: boolean;
  saleId: number | null;
  summary: SaleSummary;
  items: SaleLine[];
  onConfirm: () => void;
  onClose: () => void;
  isProcessing: boolean;
};

function InvoiceModal({ open, saleId, summary, items, onConfirm, onClose, isProcessing }: Props) {
  return (
    <Modal
      open={open}
      title="Confirmar factura"
      onClose={onClose}
      size="md"
      footer={
        <div className="button-row end">
          <button type="button" className="btn btn--ghost" onClick={onClose} disabled={isProcessing}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={onConfirm}
            disabled={isProcessing || items.length === 0}
          >
            {isProcessing ? "Generando..." : "Descargar factura"}
          </button>
        </div>
      }
    >
      <div className="invoice-preview">
        <p className="muted-text">
          Descarga el comprobante en PDF para la venta #{saleId ?? "—"}. Verifica totales y motivo antes de confirmar.
        </p>
        {items.length === 0 ? (
          <p className="muted-text">Registra una venta para activar la descarga del comprobante.</p>
        ) : (
          <ul className="compact-list">
            {items.map((line) => (
              <li key={line.device.id}>
                {line.device.sku} · {line.quantity} uds — {formatListCurrency(line.device.unit_price * line.quantity)}
              </li>
            ))}
          </ul>
        )}
        <div className="totals-card">
          <h4>Totales</h4>
          <ul className="compact-list">
            <li>Subtotal: {formatListCurrency(summary.subtotal)}</li>
            <li>Impuestos: {formatListCurrency(summary.taxAmount)}</li>
            <li className="highlight">Total: {formatListCurrency(summary.total)}</li>
          </ul>
        </div>
      </div>
    </Modal>
  );
}

export default InvoiceModal;
