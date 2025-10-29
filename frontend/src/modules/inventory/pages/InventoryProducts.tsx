import React from "react";

export default function InventoryProducts() {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Productos</h2>
      <p style={{ margin: 0, color: "#9ca3af" }}>
        Lista y gestión de dispositivos por modelo, color, capacidad y IMEI.
      </p>
      {/* En PACK 6 se reemplaza este placeholder por la tabla real (ProductsTable). */}
    </div>
  );
}
