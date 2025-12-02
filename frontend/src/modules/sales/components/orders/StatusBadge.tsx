import React from "react";

type Props = {
  value: string;
};

function StatusBadge({ value }: Props) {
  const getBadgeClass = (status: string) => {
    switch (status) {
      case "DRAFT":
        return "orders-status-badge--draft";
      case "OPEN":
        return "orders-status-badge--open";
      case "PAID":
        return "orders-status-badge--paid";
      case "CANCELLED":
        return "orders-status-badge--cancelled";
      case "REFUNDED":
        return "orders-status-badge--refunded";
      default:
        return "orders-status-badge--default";
    }
  };

  return <span className={`orders-status-badge ${getBadgeClass(value)}`}>{value}</span>;
}

export default StatusBadge;
