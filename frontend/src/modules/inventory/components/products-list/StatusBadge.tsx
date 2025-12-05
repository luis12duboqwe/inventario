import React from "react";
import "../../InventoryTable.css"; // Ensure styles are loaded

type Props = {
  value: "ACTIVE" | "INACTIVE" | string;
};

export default function StatusBadge({ value }: Props) {
  let className = "status-chip";

  if (value === "ACTIVE") {
    className += " success";
  } else if (value === "INACTIVE") {
    className += " warning"; // or a neutral style if available
  } else {
    className += " info";
  }

  return <span className={className}>{value}</span>;
}
