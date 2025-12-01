import React from "react";

import OrdersPaymentStatusBadge from "../orders-list/PaymentStatusBadge";
import OrdersStatusBadge from "../orders-list/StatusBadge";

export type OrderHeaderProps = {
  number?: string;
  status: string;
  paymentStatus: string;
  onPrint?: () => void;
  onExportPDF?: () => void;
  onCancel?: () => void;
  onMarkPaid?: () => void;
};

function Header({
  number,
  status,
  paymentStatus,
  onPrint,
  onExportPDF,
  onCancel,
  onMarkPaid,
}: OrderHeaderProps) {
  return (
    <div className="order-detail-header-container">
      <div className="order-detail-header-info">
        <div className="order-detail-header-label">Pedido</div>
        <h2 className="order-detail-header-title">{number ?? "—"}</h2>
        <div className="order-detail-header-badges">
          <OrdersPaymentStatusBadge value={paymentStatus} />
          <OrdersStatusBadge value={status} />
        </div>
      </div>
      <div className="order-detail-header-actions">
        <button onClick={onMarkPaid} className="order-detail-button-paid">
          Marcar pagado
        </button>
        <button onClick={onCancel} className="order-detail-button-cancel">
          Cancelar
        </button>
        <button onClick={onPrint} className="order-detail-button-default">
          Imprimir
        </button>
        <button onClick={onExportPDF} className="order-detail-button-default">
          PDF
        </button>
      </div>
    </div>
  );
}

export default Header;
