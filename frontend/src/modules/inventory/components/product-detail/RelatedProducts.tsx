import React from "react";

type RelatedProduct = {
  id: string;
  name: string;
};

type Props = {
  items?: RelatedProduct[];
  onOpen?: (id: string) => void;
};

export default function RelatedProducts({ items, onOpen }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ color: "#9ca3af" }}>Sin relacionados</div>;
  }

  return (
    <div style={{ display: "grid", gap: 6 }}>
      {data.map((product) => (
        <button
          key={product.id}
          onClick={() => onOpen?.(product.id)}
          style={{
            textAlign: "left",
            padding: "6px 8px",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(255,255,255,0.03)",
          }}
        >
          {product.name}
        </button>
      ))}
    </div>
  );
}
