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
    <div className="shipment-card">
      <span className="shipment-card-label">Envío</span>
      <span>{info.address ?? "—"}</span>
      <span className="shipment-card-details">
        {[info.company, info.tracking].filter(Boolean).join(" · ")}
      </span>
    </div>
  );
}

export default ShipmentCard;
