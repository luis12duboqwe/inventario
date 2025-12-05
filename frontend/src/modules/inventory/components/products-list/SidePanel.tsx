import React from "react";
import Button from "../../../../../components/ui/Button";
import StatusBadge from "./StatusBadge";
import StockBadge from "./StockBadge";
import "../../InventoryTable.css"; // Ensure styles are loaded

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
    <aside className="product-side-panel">
      <div className="product-side-panel__header">
        <h3>Vista rápida</h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cerrar
        </Button>
      </div>
      <div className="product-side-panel__image-container">
        {product.imageUrl ? (
          <img
            src={product.imageUrl}
            alt={product.name || ""}
            className="product-side-panel__image"
          />
        ) : (
          <span className="product-side-panel__no-image">Sin imagen</span>
        )}
      </div>
      <div className="product-side-panel__details">
        <div className="product-side-panel__row">
          <div className="product-side-panel__name">{product.name || "—"}</div>
          {product.status ? <StatusBadge value={product.status} /> : null}
        </div>
        <div className="product-side-panel__sku">{product.sku || "—"}</div>
        <div className="product-side-panel__row">
          <div className="product-side-panel__price">
            {Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(
              product.price || 0,
            )}
          </div>
          <StockBadge qty={product.stock ?? 0} />
        </div>
        <div className="product-side-panel__category">Categoría: {product.category || "—"}</div>
      </div>
    </aside>
  );
}
