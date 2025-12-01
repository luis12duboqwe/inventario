import React from "react";

import StatusBadge from "./StatusBadge";
import StockBadge from "./StockBadge";

export type ProductCardData = {
  id: string;
  name: string;
  sku?: string;
  price: number;
  imageUrl?: string;
  status: "ACTIVE" | "INACTIVE";
  stock: number;
};

type Props = {
  items?: ProductCardData[];
  onClick?: (id: string) => void;
};

export default function Grid({ items, onClick }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ padding: 12, color: "#9ca3af" }}>Sin productos</div>;
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px,1fr))",
        gap: 12,
      }}
    >
      {data.map((product) => (
        <div
          key={product.id}
          role="button"
          tabIndex={0}
          onClick={() => onClick?.(product.id)}
          onKeyDown={(e) => {
            if (onClick && (e.key === "Enter" || e.key === " ")) {
              e.preventDefault();
              onClick(product.id);
            }
          }}
          style={{
            cursor: onClick ? "pointer" : "default",
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.08)",
            overflow: "hidden",
            background: "rgba(255,255,255,0.03)",
          }}
        >
          <div
            style={{
              width: "100%",
              aspectRatio: "4 / 3",
              background: "#0f172a",
              display: "grid",
              placeItems: "center",
            }}
          >
            {product.imageUrl ? (
              <img
                src={product.imageUrl}
                alt={product.name}
                style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "cover" }}
              />
            ) : (
              <span style={{ color: "#64748b" }}>Sin imagen</span>
            )}
          </div>
          <div style={{ padding: 12, display: "grid", gap: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div
                style={{
                  fontWeight: 700,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {product.name}
              </div>
              <StatusBadge value={product.status} />
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8" }}>{product.sku || "—"}</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>{Intl.NumberFormat().format(product.price)}</div>
              <StockBadge qty={product.stock} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
