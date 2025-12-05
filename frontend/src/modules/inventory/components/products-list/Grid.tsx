import React from "react";
import StatusBadge from "./StatusBadge";
import StockBadge from "./StockBadge";
import "../../InventoryTable.css"; // Ensure styles are loaded

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
    return <div className="product-grid__empty">Sin productos</div>;
  }

  return (
    <div className="product-grid">
      {data.map((product) => (
        <div
          key={product.id}
          role="button"
          tabIndex={0}
          className={`product-card ${onClick ? "cursor-pointer" : "cursor-default"}`}
          onClick={() => onClick?.(product.id)}
          onKeyDown={(e) => {
            if (onClick && (e.key === "Enter" || e.key === " ")) {
              e.preventDefault();
              onClick(product.id);
            }
          }}
        >
          <div className="product-card__image-container">
            {product.imageUrl ? (
              <img src={product.imageUrl} alt={product.name} className="product-card__image" />
            ) : (
              <span className="product-card__no-image">Sin imagen</span>
            )}
          </div>
          <div className="product-card__content">
            <div className="product-card__header">
              <div className="product-card__title" title={product.name}>
                {product.name}
              </div>
              <StatusBadge value={product.status} />
            </div>
            <div className="product-card__sku">{product.sku || "—"}</div>
            <div className="product-card__footer">
              <div className="product-card__price">
                {Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(
                  product.price,
                )}
              </div>
              <StockBadge qty={product.stock} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
