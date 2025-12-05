import React from "react";
import "../../InventoryTable.css"; // Ensure styles are loaded

type Props = {
  qty: number;
};

export default function StockBadge({ qty }: Props) {
  let className = "status-chip";

  if (qty <= 0) {
    className += " danger";
  } else if (qty < 5) {
    className += " warning";
  } else {
    className += " info";
  }

  return <span className={className}>{qty}</span>;
}
