import React from "react";

type Supplier = {
  name: string;
  contact?: string;
  phone?: string;
  email?: string;
  taxId?: string;
};

type Props = {
  supplier?: Supplier;
};

export default function SupplierCard({ supplier }: Props) {
  const data = supplier || { name: "—" };
  const details = [data.contact, data.phone, data.email, data.taxId].filter(Boolean).join(" · ");

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Proveedor</div>
      <div style={{ fontWeight: 700 }}>{data.name}</div>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>{details}</div>
    </div>
  );
}
