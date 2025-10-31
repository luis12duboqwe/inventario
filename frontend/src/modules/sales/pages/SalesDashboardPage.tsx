import React from "react";
import { SummaryCards } from "../components/common";

export default function SalesDashboardPage() {
  const cards = [
    { label: "Ventas hoy", value: "—" },
    { label: "Ticket promedio", value: "—" },
    { label: "Top producto", value: "—" },
    { label: "Devoluciones hoy", value: "—" },
  ];

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <SummaryCards items={cards} />
    </div>
  );
}
