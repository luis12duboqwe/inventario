import React from "react";

import StatusBadge from "./StatusBadge";
import StockBadge from "./StockBadge";

type ProductInfo = {
  name?: string;
  sku?: string;
  price?: number;
  status?: string;
  stock?: number;
  imageUrl?: string;
  category?: string;
};

type Props = {
  product?: ProductInfo;
  onClose?: () => void;
};

export default function SidePanel({ product, onClose }: Props) {
  if (!product) {
    return null;
  }

  return (
    <aside
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        bottom: 0,
        width: 420,
        background: "#0b1220",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
        padding: 16,
        overflow: "auto",
        zIndex: 40,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={{ margin: 0 }}>Vista rápida</h3>
        <button onClick={onClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
          Cerrar
        </button>
      </div>
      <div
        style={{
          width: "100%",
          aspectRatio: "4 / 3",
          background: "#0f172a",
          borderRadius: 8,
          marginBottom: 8,
          display: "grid",
          placeItems: "center",
        }}
      >
        {product.imageUrl ? (
          <img
            src={product.imageUrl}
            alt={product.name || ""}
            style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "cover" }}
          />
        ) : (
          <span style={{ color: "#64748b" }}>Sin imagen</span>
        )}
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700 }}>{product.name || "—"}</div>
          {product.status ? <StatusBadge value={product.status} /> : null}
        </div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>{product.sku || "—"}</div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>{Intl.NumberFormat().format(product.price || 0)}</div>
          <StockBadge qty={product.stock ?? 0} />
        </div>
        <div style={{ fontSize: 12, color: "#94a3b8" }}>Categoría: {product.category || "—"}</div>
      </div>
    </aside>
  );
}
