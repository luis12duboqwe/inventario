import React from "react";

export type OrderCustomer = {
  id?: string;
  name?: string;
  phone?: string;
  email?: string;
  taxId?: string;
};

export type OrderCustomerCardProps = {
  customer?: OrderCustomer | null;
};

function CustomerCard({ customer }: OrderCustomerCardProps) {
  const info = customer ?? {};

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        display: "grid",
        gap: 4,
      }}
    >
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Cliente</span>
      <strong>{info.name ?? "—"}</strong>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>
        {[info.phone, info.email].filter(Boolean).join(" · ")}
      </span>
      {info.taxId ? <span style={{ fontSize: 12, color: "#94a3b8" }}>RTN: {info.taxId}</span> : null}
    </div>
  );
}

export default CustomerCard;
