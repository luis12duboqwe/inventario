import React from "react";

export default function RepairsPending() {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Órdenes pendientes</h2>
      <p style={{ margin: 0, color: "#9ca3af" }}>
        Gestor de órdenes activas; filtro por sucursal, técnico y estado.
      </p>
      {/* En PACK 5 se conecta a la tabla real y formularios. */}
    </div>
  );
}
