import React from "react";

export default function OperationsPOS() {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>POS / Caja</h2>
      <p style={{ margin: 0, color: "#9ca3af" }}>
        Registro de ventas, descuentos, impuestos y cierre de caja.
      </p>
      {/* En packs posteriores se integrará el formulario POS real y la tabla de líneas. */}
    </div>
  );
}
