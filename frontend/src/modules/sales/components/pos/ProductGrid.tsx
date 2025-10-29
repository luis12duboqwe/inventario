import React from "react";

export type ProductCard = {
  id: string;
  name: string;
  sku: string;
  price: number;
  thumbnail?: string;
  stock?: number;
};

type Props = {
  items?: ProductCard[];
  loading?: boolean;
  onPick?: (id: string) => void;
};

const formatter = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  maximumFractionDigits: 2,
});

export default function ProductGrid({ items, loading, onPick }: Props) {
  const data = Array.isArray(items) ? items : [];
  if (loading) return <div style={{ padding: 12 }}>Cargando…</div>;
  if (!data.length) return <div style={{ padding: 12, color: "#9ca3af" }}>Sin productos</div>;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
        gap: 12,
      }}
    >
      {data.map((p) => (
        <button
          key={p.id}
          onClick={() => onPick?.(p.id)}
          style={{
            textAlign: "left",
            padding: 10,
            borderRadius: 12,
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div
            style={{
              height: 96,
              background: "rgba(255,255,255,0.03)",
              borderRadius: 10,
              marginBottom: 8,
              display: "grid",
              placeItems: "center",
            }}
          >
            {p.thumbnail ? (
              <img
                src={p.thumbnail}
                alt={p.name}
                style={{ maxHeight: "100%", maxWidth: "100%", borderRadius: 8 }}
              />
            ) : (
              <span style={{ color: "#94a3b8" }}>Imagen</span>
            )}
          </div>
          <div style={{ fontWeight: 600 }}>{p.name}</div>
          <div style={{ color: "#94a3b8", fontSize: 12 }}>{p.sku}</div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
            <span>{formatter.format(p.price)}</span>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>
              Stock: {p.stock ?? "-"}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
