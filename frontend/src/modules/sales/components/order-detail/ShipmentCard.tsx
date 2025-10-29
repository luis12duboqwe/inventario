import React from "react";

type Shipment = {
  carrier?: string;
  code?: string;
  eta?: string;
  address?: string;
};

type Props = {
  data?: Shipment;
};

function ShipmentCard({ data }: Props) {
  const shipment = data || {};

  return (
    <div
      style={{
        padding: 12,
        borderRadius: 12,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255, 255, 255, 0.08)",
      }}
    >
      <div style={{ fontSize: 12, color: "#94a3b8" }}>Envío</div>
      <div>Transportista: {shipment.carrier || "—"}</div>
      <div>Guía: {shipment.code || "—"}</div>
      <div>ETA: {shipment.eta || "—"}</div>
      <div>Dirección: {shipment.address || "—"}</div>
    </div>
  );
}

export default ShipmentCard;
