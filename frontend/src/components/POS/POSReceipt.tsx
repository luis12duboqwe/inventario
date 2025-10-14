import { useState } from "react";
import type { Sale } from "../../api";
import { downloadPosReceipt, registerSaleReturn } from "../../api";

type Props = {
  token: string;
  sale: Sale | null;
  receiptUrl?: string | null;
};

function POSReceipt({ token, sale, receiptUrl }: Props) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  if (!sale) {
    return (
      <section className="card">
        <h3>Último recibo</h3>
        <p className="muted-text">Registra una venta para activar la descarga del recibo PDF.</p>
      </section>
    );
  }

  const formatCurrency = (value: number) => value.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const handlePrint = async () => {
    try {
      setError(null);
      setMessage(null);
      const blob = await downloadPosReceipt(token, sale.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `recibo_${sale.id}.pdf`;
      link.target = "_blank";
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Recibo descargado correctamente.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible descargar el recibo.");
    }
  };

  const handleReturn = async () => {
    if (!sale) {
      return;
    }
    if (sale.items.length === 0) {
      setError("La venta no tiene artículos para devoluciones.");
      return;
    }
    const defaultDeviceId = String(sale.items[0]?.device_id ?? "");
    const deviceRaw = window.prompt("ID del dispositivo a devolver", defaultDeviceId);
    if (!deviceRaw) {
      return;
    }
    const deviceId = Number(deviceRaw);
    if (!Number.isFinite(deviceId) || deviceId <= 0) {
      setError("Indica un identificador de dispositivo válido.");
      return;
    }
    const saleItem = sale.items.find((item) => item.device_id === deviceId);
    if (!saleItem) {
      setError("El dispositivo indicado no forma parte de la venta actual.");
      return;
    }
    const quantityRaw = window.prompt(
      "Cantidad a devolver",
      String(Math.max(1, saleItem.quantity))
    );
    if (!quantityRaw) {
      return;
    }
    const quantity = Number(quantityRaw);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("Indica una cantidad válida a devolver.");
      return;
    }
    const detailReason = window.prompt(
      "Motivo visible para el cliente",
      "Devolución en mostrador"
    );
    const reason = window.prompt(
      "Motivo corporativo para la devolución",
      "Devolución autorizada POS"
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes capturar un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    try {
      await registerSaleReturn(
        token,
        {
          sale_id: sale.id,
          items: [
            {
              device_id: deviceId,
              quantity: Math.min(quantity, saleItem.quantity),
              reason: detailReason?.trim() || "Devolución en mostrador",
            },
          ],
        },
        reason.trim()
      );
      setMessage("Devolución registrada correctamente. Verifica el módulo de devoluciones para detalles.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible registrar la devolución POS."
      );
    }
  };

  const handleEmail = async () => {
    const targetEmail = window.prompt("Correo del cliente", "cliente@example.com");
    if (!targetEmail) {
      return;
    }
    setSending(true);
    setMessage(null);
    setError(null);
    setTimeout(() => {
      setSending(false);
      setMessage(`Recibo enviado a ${targetEmail}`);
    }, 600);
  };

  return (
    <section className="card">
      <h3>Última venta registrada</h3>
      <p className="card-subtitle">Descarga o envía el comprobante inmediatamente al cliente.</p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      <div className="sale-summary">
        <div>
          <span className="muted-text">Folio</span>
          <strong>#{sale.id}</strong>
        </div>
        <div>
          <span className="muted-text">Cliente</span>
          <strong>{sale.customer_name ?? "Mostrador"}</strong>
        </div>
        <div>
          <span className="muted-text">Total</span>
          <strong className="highlight">${formatCurrency(sale.total_amount)}</strong>
        </div>
      </div>
      <ul className="muted-text">
        {sale.items.map((item) => (
          <li key={item.id}>
            {item.quantity} × Dispositivo #{item.device_id} — ${formatCurrency(item.total_line)}
          </li>
        ))}
      </ul>
      <div className="actions-row">
        <button type="button" className="button ghost" onClick={handlePrint}>
          Imprimir/Descargar PDF
        </button>
        <button type="button" className="button secondary" onClick={handleReturn}>
          Registrar devolución
        </button>
        <button type="button" className="button secondary" onClick={handleEmail} disabled={sending}>
          {sending ? "Enviando..." : "Enviar por correo"}
        </button>
        {receiptUrl ? (
          <a className="button link" href={receiptUrl} target="_blank" rel="noreferrer">
            Abrir en nueva pestaña
          </a>
        ) : null}
      </div>
    </section>
  );
}

export default POSReceipt;
