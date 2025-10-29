import React from "react";

type Customer = {
  name: string;
  phone?: string;
  email?: string;
  document?: string;
};

type Props = {
  customer?: Customer;
};

function CustomerCard({ customer }: Props) {
  const c = customer || { name: "—" };
  const details = [c.phone, c.email, c.document].filter(Boolean).join(" · ");

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Cliente</div>
      <div style={{ fontWeight: 700 }}>{c.name}</div>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>{details}</div>
    </div>
  );
}

export default CustomerCard;
