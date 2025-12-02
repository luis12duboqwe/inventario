import React from "react";

export type PaymentStatusBadgeProps = {
  value: "UNPAID" | "PARTIAL" | "PAID" | "REFUNDED" | string;
};

function PaymentStatusBadge({ value }: PaymentStatusBadgeProps) {
  const getBadgeClass = (status: string) => {
    switch (status) {
      case "UNPAID":
        return "orders-payment-status-badge--unpaid";
      case "PARTIAL":
        return "orders-payment-status-badge--partial";
      case "PAID":
        return "orders-payment-status-badge--paid";
      case "REFUNDED":
        return "orders-payment-status-badge--refunded";
      default:
        return "orders-payment-status-badge--default";
    }
  };

  return <span className={`orders-payment-status-badge ${getBadgeClass(value)}`}>{value}</span>;
}

export default PaymentStatusBadge;
