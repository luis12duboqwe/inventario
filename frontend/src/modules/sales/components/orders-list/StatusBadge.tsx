import React from "react";

export type StatusBadgeProps = {
  value: "DRAFT" | "OPEN" | "COMPLETED" | "CANCELLED" | string;
};

function StatusBadge({ value }: StatusBadgeProps) {
  let modifierClass = "";
  switch (value) {
    case "DRAFT":
      modifierClass = "orders-list-status-badge--draft";
      break;
    case "OPEN":
      modifierClass = "orders-list-status-badge--open";
      break;
    case "COMPLETED":
      modifierClass = "orders-list-status-badge--completed";
      break;
    case "CANCELLED":
      modifierClass = "orders-list-status-badge--cancelled";
      break;
    default:
      modifierClass = "";
  }

  return <span className={`orders-list-status-badge ${modifierClass}`}>{value}</span>;
}

export default StatusBadge;
