import React from "react";

type Product = {
  id: string;
  sku?: string;
  name: string;
  price: number;
  stock?: number;
  image?: string;
};

type Props = {
  items: Product[];
  onPick?: (product: Product) => void;
};

export default function ProductGrid({ items, onPick }: Props) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
        gap: 10,
      }}
    >
      {data.map((product) => (
        <button
          key={product.id}
          onClick={() => onPick?.(product)}
          style={{
            textAlign: "left",
            padding: 10,
            borderRadius: 12,
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(255,255,255,0.02)",
          }}
        >
          <div
            style={{
              height: 110,
              borderRadius: 8,
              background: "#0f172a",
              marginBottom: 8,
              display: "grid",
              placeItems: "center",
              overflow: "hidden",
            }}
          >
            {product.image ? (
              <img
                src={product.image}
                alt={product.name}
                style={{ maxWidth: "100%", maxHeight: "100%" }}
              />
            ) : (
              <span style={{ color: "#64748b", fontSize: 12 }}>Sin imagen</span>
            )}
          </div>
          <div style={{ fontWeight: 700 }}>{product.name}</div>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>{product.sku ?? "—"}</div>
          <div style={{ marginTop: 4 }}>{Intl.NumberFormat().format(product.price)}</div>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>
            Stock: {product.stock ?? "—"}
          </div>
        </button>
      ))}
    </div>
  );
}
