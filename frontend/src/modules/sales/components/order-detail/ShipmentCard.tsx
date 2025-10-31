import React from "react";

export type OrderShipment = {
  address?: string;
  company?: string;
  tracking?: string;
};

export type OrderShipmentCardProps = {
  shipment?: OrderShipment | null;
};

function ShipmentCard({ shipment }: OrderShipmentCardProps) {
  const info = shipment ?? {};

  if (!info.address && !info.company && !info.tracking) {
    return null;
  }

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
      <span style={{ fontSize: 12, color: "#94a3b8" }}>Envío</span>
      <span>{info.address ?? "—"}</span>
      <span style={{ fontSize: 12, color: "#94a3b8" }}>
        {[info.company, info.tracking].filter(Boolean).join(" · ")}
      </span>
    </div>
  );
}

export default ShipmentCard;
