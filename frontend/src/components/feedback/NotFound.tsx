import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div style={{ minHeight: "60vh", display: "grid", placeItems: "center", padding: 24 }}>
      <div style={{ textAlign: "center" }}>
        <h1 style={{ margin: 0, fontSize: 32 }}>404</h1>
        <p style={{ color: "#94a3b8", marginTop: 8 }}>Página no encontrada</p>
        <Link
          to="/dashboard"
          style={{
            display: "inline-block",
            marginTop: 12,
            padding: "10px 14px",
            borderRadius: 10,
            background: "#2563eb",
            color: "#fff",
            textDecoration: "none",
          }}
        >
          Ir al dashboard
        </Link>
      </div>
    </div>
  );
}
