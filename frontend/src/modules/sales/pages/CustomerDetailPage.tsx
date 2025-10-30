import React, { useState } from "react";
import { CustomerDetailCard } from "../components/customers";

type CustomerProfile = {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  tier?: string;
  tags?: string[];
  notes?: string;
};

export function CustomerDetailPage() {
  const [profile] = useState<CustomerProfile>({
    id: "demo",
    name: "Cliente Demo",
    email: "demo@x.com",
    phone: "999",
    tier: "STANDARD",
    tags: ["frecuente"],
    notes: "—",
  });

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <CustomerDetailCard value={profile} />
      <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700 }}>Historial de compras</div>
        {/* TODO(wire) tabla de ventas del cliente */}
      </div>
    </div>
  );
}
