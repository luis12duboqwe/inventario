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
    <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12 }}>
      <div style={{ fontWeight: 700, fontSize: 18 }}>{current.name ?? "—"}</div>
      <div style={{ color: "#94a3b8", fontSize: 12 }}>
        {current.email ?? "—"} · {current.phone ?? "—"}
      </div>
      <div style={{ marginTop: 8 }}>
        <b>Tier:</b> {current.tier ?? "—"}
      </div>
      <div style={{ marginTop: 8 }}>
        <b>Etiquetas:</b> {(current.tags ?? []).join(", ") || "—"}
      </div>
      {!!current.notes && (
        <div style={{ marginTop: 8 }}>
          <b>Notas:</b> {current.notes}
        </div>
      )}
    </div>
  );
}
