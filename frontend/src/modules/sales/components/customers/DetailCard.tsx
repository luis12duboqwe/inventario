import React from "react";

type Customer = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  tier?: string;
  tags?: string[];
  notes?: string;
};

type Props = {
  value: Customer;
};

export default function DetailCard({ value }: Props) {
  const current = value ?? ({} as Customer);
  return (
    <div className="customer-detail-card">
      <div className="customer-detail-name">{current.name ?? "—"}</div>
      <div className="customer-detail-contact">
        {current.email ?? "—"} · {current.phone ?? "—"}
      </div>
      <div className="customer-detail-row">
        <b>Tier:</b> {current.tier ?? "—"}
      </div>
      <div className="customer-detail-row">
        <b>Etiquetas:</b> {(current.tags ?? []).join(", ") || "—"}
      </div>
      {!!current.notes && (
        <div className="customer-detail-row">
          <b>Notas:</b> {current.notes}
        </div>
      )}
    </div>
  );
}
