import { useState } from "react";
import type { Sale } from "../../../api";
import { downloadPosReceipt, registerSaleReturn } from "../../../api";

type Props = {
  token: string;
  sale: Sale | null;
  receiptUrl?: string | null;
};

function ReceiptPreview({ token, sale, receiptUrl }: Props) {
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

  const formatCurrency = (value: number) => value.toLocaleString("es-HN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

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
      String(Math.max(1, saleItem.quantity)),
    );
    if (!quantityRaw) {
      return;
    }
    const quantity = Number(quantityRaw);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("Indica una cantidad válida a devolver.");
      return;
    }
    if (!saleItem.quantity || saleItem.quantity <= 0) {
      setError("No se pudo determinar la cantidad vendida del dispositivo.");
      return;
    }
    const detailReason = window.prompt(
      "Motivo visible para el cliente",
      "Devolución en mostrador",
    );
    const reason = window.prompt(
      "Motivo corporativo para la devolución",
      "Devolución autorizada POS",
    );
    if (!reason || reason.trim().length < 5) {
      setError("Debes capturar un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    const normalizedQuantity = Math.min(Math.max(1, quantity), saleItem.quantity);
    const unitPrice = saleItem.total_line / saleItem.quantity;
    const refundAmount = Number((unitPrice * normalizedQuantity).toFixed(2));
    if (!Number.isFinite(refundAmount) || refundAmount <= 0) {
      setError("No se pudo calcular el monto a reembolsar para la devolución.");
      return;
    }
    const breakdownEntries = Object.entries(sale.payment_breakdown ?? {}).filter(([, value]) =>
      Number.isFinite(value) && value > 0,
    );
    const breakdown: Record<string, number> = {};
    if (breakdownEntries.length > 0) {
      const totalPaid = breakdownEntries.reduce((acc, [, value]) => acc + value, 0);
      let remaining = refundAmount;
      breakdownEntries.forEach(([method, value], index) => {
        if (totalPaid <= 0) {
          return;
        }
        if (index === breakdownEntries.length - 1) {
          breakdown[method] = Number(remaining.toFixed(2));
          remaining = 0;
          return;
        }
        const ratio = value / totalPaid;
        const portion = Number((refundAmount * ratio).toFixed(2));
        breakdown[method] = portion;
        remaining = Number((remaining - portion).toFixed(2));
      });
      if (remaining !== 0) {
        const fallbackMethod = breakdownEntries[breakdownEntries.length - 1]?.[0] ?? sale.payment_method;
        breakdown[fallbackMethod] = Number(((breakdown[fallbackMethod] ?? 0) + remaining).toFixed(2));
      }
    } else {
      breakdown[sale.payment_method] = refundAmount;
    }
    const breakdownSummary = Object.entries(breakdown)
      .map(([method, amount]) => `${method}: $${formatCurrency(amount)}`)
      .join(" · ");
    const confirmed = window.confirm(
      `Reintegra ${breakdownSummary}. ¿Deseas confirmar la devolución?`,
    );
    if (!confirmed) {
      setMessage(null);
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
              quantity: normalizedQuantity,
              reason: detailReason?.trim() || "Devolución en mostrador",
              category: "cliente",
            },
          ],
        },
        reason.trim(),
      );
      setMessage(
        `Devolución registrada. Reintegra ${breakdownSummary} y actualiza la caja correspondiente.`,
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible registrar la devolución POS.",
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
        <button type="button" className="btn btn--ghost" onClick={handlePrint}>
          Imprimir/Descargar PDF
        </button>
        <button type="button" className="btn btn--secondary" onClick={handleReturn}>
          Registrar devolución
        </button>
        <button type="button" className="btn btn--secondary" onClick={handleEmail} disabled={sending}>
          {sending ? "Enviando..." : "Enviar por correo"}
        </button>
        {receiptUrl ? (
          <a className="btn btn--link" href={receiptUrl} target="_blank" rel="noreferrer">
            Abrir en nueva pestaña
          </a>
        ) : null}
      </div>
    </section>
  );
}

export default ReceiptPreview;
