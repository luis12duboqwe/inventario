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

const currency = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

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
  }, [orderInfo.number, orderInfo.date, orderInfo.total, customerInfo.name, customerInfo.taxId, businessInfo.taxId, docType]);

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
    <div
      style={{
        width: 320,
        padding: 12,
        color: "#111827",
        background: "#ffffff",
        fontFamily: "monospace",
        fontSize: 12,
        borderRadius: 8,
      }}
    >
      <div style={{ textAlign: "center", fontWeight: 700 }}>{businessInfo.name ?? "SOFTMOBILE"}</div>
      {businessInfo.address ? <div style={{ textAlign: "center" }}>{businessInfo.address}</div> : null}
      {businessInfo.phone ? <div style={{ textAlign: "center" }}>{businessInfo.phone}</div> : null}
      {businessInfo.taxId ? <div style={{ textAlign: "center" }}>RTN: {businessInfo.taxId}</div> : null}
      <hr />
      <div style={{ fontWeight: 600 }}>{docType}</div>
      <div>Pedido: {orderInfo.number ?? "—"}</div>
      <div>Fecha: {orderInfo.date ? new Date(orderInfo.date).toLocaleString() : "—"}</div>
      {customerInfo.name ? <div>Cliente: {customerInfo.name}</div> : null}
      {customerInfo.taxId ? <div>RTN: {customerInfo.taxId}</div> : null}
      <hr />
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <tbody>
          {items.map((item, index) => (
            <tr key={`${item.name}-${index}`}>
              <td style={{ width: "55%" }}>{item.name}</td>
              <td style={{ width: "15%", textAlign: "right" }}>{item.qty}</td>
              <td style={{ width: "15%", textAlign: "right" }}>{currency.format(item.price)}</td>
              <td style={{ width: "15%", textAlign: "right" }}>{currency.format(item.subtotal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <hr />
      <div style={{ display: "grid", gap: 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Subtotal</span>
          <span>{currency.format(orderInfo.subtotal ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Descuento</span>
          <span>{currency.format(orderInfo.discount ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Impuestos</span>
          <span>{currency.format(orderInfo.taxes ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
          <span>Total</span>
          <span>{currency.format(orderInfo.total ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Pagado</span>
          <span>{currency.format(orderInfo.paid ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Cambio</span>
          <span>{currency.format(orderInfo.change ?? 0)}</span>
        </div>
      </div>
      <hr />
      <div style={{ textAlign: "center" }}>¡Gracias por su compra!</div>
      {qrSrc ? (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
          <img src={qrSrc} alt="Código QR de validación" style={{ width: 120, height: 120 }} />
          <span style={{ fontSize: 10, color: "#64748b" }}>Escanea para validar el comprobante</span>
        </div>
      ) : null}
    </div>
  );
}

export default ReceiptTicket;
