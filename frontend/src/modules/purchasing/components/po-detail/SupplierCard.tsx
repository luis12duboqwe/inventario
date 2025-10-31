import React from "react";

type Supplier = {
  name?: string;
  phone?: string;
  email?: string;
  taxId?: string;
};

type Props = {
  s?: Supplier;
};

const cardStyle: React.CSSProperties = {
  padding: 12,
  borderRadius: 12,
  background: "rgba(255, 255, 255, 0.04)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  display: "grid",
  gap: 4,
};

export default function SupplierCard({ s }: Props) {
  const supplier = s || {};
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Proveedor</div>
      <div style={{ fontWeight: 700 }}>{supplier.name || "—"}</div>
      <div style={{ fontSize: 12, color: "#94a3b8" }}>
        {supplier.phone || ""}
        {supplier.email ? ` · ${supplier.email}` : ""}
      </div>
      {supplier.taxId ? (
        <div style={{ fontSize: 12, color: "#94a3b8" }}>RTN: {supplier.taxId}</div>
      ) : null}
    </div>
  );
}
