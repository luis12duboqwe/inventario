import React from "react";

export default function SkipLink() {
  return (
    <a
      href="#main-content"
      style={{
        position: "absolute",
        left: 8,
        top: 8,
        padding: "8px 12px",
        borderRadius: 10,
        transform: "translateY(-150%)",
        background: "#111827",
        color: "#e5e7eb",
        textDecoration: "none",
      }}
      onFocus={(e) => {
        (e.currentTarget.style as any).transform = "translateY(0)";
      }}
      onBlur={(e) => {
        (e.currentTarget.style as any).transform = "translateY(-150%)";
      }}
    >
      Ir al contenido principal
    </a>
  );
}
