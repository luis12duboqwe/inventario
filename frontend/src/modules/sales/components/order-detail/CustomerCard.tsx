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
    <div className="customer-card">
      <span className="customer-card-label">Cliente</span>
      <strong>{info.name ?? "—"}</strong>
      <span className="customer-card-details">
        {[info.phone, info.email].filter(Boolean).join(" · ")}
      </span>
      {info.taxId ? <span className="customer-card-details">RTN: {info.taxId}</span> : null}
    </div>
  );
}

export default CustomerCard;
