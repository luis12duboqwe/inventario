import React from "react";

export type POSQuickProduct = {
  id: string;
  name: string;
  price: number;
  imageUrl?: string;
};

export type POSQuickGridProps = {
  items?: POSQuickProduct[];
  onPick?: (id: string) => void;
};

const currency = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function QuickGrid({ items, onPick }: POSQuickGridProps) {
  const data = Array.isArray(items) ? items : [];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
      {data.map((product) => (
        <button
          key={product.id}
          onClick={() => onPick?.(product.id)}
          style={{
            textAlign: "left",
            borderRadius: 12,
            border: "1px solid rgba(255, 255, 255, 0.08)",
            overflow: "hidden",
            background: "rgba(255, 255, 255, 0.03)",
            display: "grid",
            padding: 0,
          }}
        >
          <div
            style={{
              width: "100%",
              aspectRatio: "1 / 1",
              background: "#0f172a",
              display: "grid",
              placeItems: "center",
              overflow: "hidden",
            }}
          >
            {product.imageUrl ? (
              <img
                src={product.imageUrl}
                alt={product.name}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            ) : (
              <span style={{ color: "#64748b" }}>Sin imagen</span>
            )}
          </div>
          <div style={{ padding: 8, display: "grid", gap: 4 }}>
            <span
              style={{
                fontWeight: 700,
                fontSize: 13,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {product.name}
            </span>
            <span style={{ fontSize: 12 }}>{currency.format(product.price)}</span>
          </div>
        </button>
      ))}
    </div>
  );
}

export default QuickGrid;
