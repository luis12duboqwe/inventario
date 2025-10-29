import React from "react";

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
    </div>
  );
}

export default ReceiptTicket;
