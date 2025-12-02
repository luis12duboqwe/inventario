import React, { useEffect, useMemo, useState } from "react";
import QRCode from "qrcode";

export type ReceiptBusiness = {
  name?: string;
  address?: string;
  phone?: string;
  taxId?: string;
};

export type ReceiptOrderItem = {
  name: string;
  qty: number;
  price: number;
  subtotal: number;
};

export type ReceiptOrder = {
  number?: string;
  date?: string;
  items?: ReceiptOrderItem[];
  subtotal?: number;
  discount?: number;
  taxes?: number;
  total?: number;
  paid?: number;
  change?: number;
};

export type ReceiptCustomer = {
  name?: string;
  taxId?: string;
};

export type ReceiptTicketProps = {
  business?: ReceiptBusiness;
  order?: ReceiptOrder;
  customer?: ReceiptCustomer;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function ReceiptTicket({ business, order, customer }: ReceiptTicketProps) {
  const businessInfo = business ?? {};
  const orderInfo = order ?? {};
  const items = Array.isArray(orderInfo.items) ? orderInfo.items : [];
  const customerInfo = customer ?? {};
  const docType = customerInfo.taxId ? "Factura" : "Ticket";
  const [qrSrc, setQrSrc] = useState<string | null>(null);

  const qrPayload = useMemo(() => {
    return {
      number: orderInfo.number ?? null,
      issuedAt: orderInfo.date ?? null,
      total: orderInfo.total ?? null,
      customer: customerInfo.name ?? null,
      customerTaxId: customerInfo.taxId ?? null,
      businessTaxId: businessInfo.taxId ?? null,
      type: docType.toLowerCase(),
    };
  }, [
    orderInfo.number,
    orderInfo.date,
    orderInfo.total,
    customerInfo.name,
    customerInfo.taxId,
    businessInfo.taxId,
    docType,
  ]);

  useEffect(() => {
    let alive = true;
    const generate = async () => {
      try {
        const dataUrl = await QRCode.toDataURL(JSON.stringify(qrPayload));
        if (alive) setQrSrc(dataUrl);
      } catch {
        if (alive) setQrSrc(null);
      }
    };
    void generate();
    return () => {
      alive = false;
    };
  }, [qrPayload]);

  return (
    <div className="receipt-ticket">
      <div className="receipt-header">{businessInfo.name ?? "SOFTMOBILE"}</div>
      {businessInfo.address ? (
        <div className="receipt-text-center">{businessInfo.address}</div>
      ) : null}
      {businessInfo.phone ? <div className="receipt-text-center">{businessInfo.phone}</div> : null}
      {businessInfo.taxId ? (
        <div className="receipt-text-center">RTN: {businessInfo.taxId}</div>
      ) : null}
      <hr />
      <div className="receipt-title">{docType}</div>
      <div>Pedido: {orderInfo.number ?? "—"}</div>
      <div>Fecha: {orderInfo.date ? new Date(orderInfo.date).toLocaleString() : "—"}</div>
      {customerInfo.name ? <div>Cliente: {customerInfo.name}</div> : null}
      {customerInfo.taxId ? <div>RTN: {customerInfo.taxId}</div> : null}
      <hr />
      <table className="receipt-table">
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.name}-${index}`}>
              <td className="receipt-col-name">{item.name}</td>
              <td className="receipt-col-qty">{item.qty}</td>
              <td className="receipt-col-price">{currency.format(item.price)}</td>
              <td className="receipt-col-subtotal">{currency.format(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div className="receipt-totals">
        <div className="receipt-row">
          <span>Subtotal</span>
          <span>{currency.format(orderInfo.subtotal ?? 0)}</span>
        </div>
        <div className="receipt-row">
          <span>Descuento</span>
          <span>{currency.format(orderInfo.discount ?? 0)}</span>
        </div>
        <div className="receipt-row">
          <span>Impuestos</span>
          <span>{currency.format(orderInfo.taxes ?? 0)}</span>
        </div>
        <div className="receipt-row-bold">
          <span>Total</span>
          <span>{currency.format(orderInfo.total ?? 0)}</span>
        </div>
        <div className="receipt-row">
          <span>Pagado</span>
          <span>{currency.format(orderInfo.paid ?? 0)}</span>
        </div>
        <div className="receipt-row">
          <span>Cambio</span>
          <span>{currency.format(orderInfo.change ?? 0)}</span>
        </div>
      </div>
      <hr />
      <div className="receipt-text-center">¡Gracias por su compra!</div>
      {qrSrc ? (
        <div className="receipt-qr-container">
          <img src={qrSrc} alt="Código QR de validación" className="receipt-qr-image" />
          <span className="receipt-qr-text">Escanea para validar el comprobante</span>
        </div>
      ) : null}
    </div>
  );
}

export default ReceiptTicket;
