import React from "react";

import type { InventoryAvailabilityRecord } from "@api/inventory";

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
  availabilityByReference?: Record<string, InventoryAvailabilityRecord>;
  availabilityLoading?: boolean;
};

const buildAvailabilityReference = (product: Product): string => {
  const normalizedSku = product.sku?.trim().toLowerCase();
  if (normalizedSku) {
    return normalizedSku;
  }
  const numericId = Number(product.id);
  if (Number.isFinite(numericId)) {
    return `device:${Math.trunc(numericId)}`;
  }
  return String(product.id);
};

export default function ProductGrid({
  items,
  onPick,
  availabilityByReference,
  availabilityLoading,
}: Props) {
  const data = Array.isArray(items) ? items : [];
  return (
    <div className="pos-product-grid">
      {data.map((product) => {
        const reference = buildAvailabilityReference(product);
        const availability = availabilityByReference?.[reference];
        const availabilitySummary = availability
          ? availability.stores.map((store) => `${store.store_name}: ${store.quantity}`).join(" · ")
          : undefined;
        return (
          <button key={product.id} onClick={() => onPick?.(product)} className="pos-product-card">
            <div className="pos-product-card__image">
              {product.image ? (
                <img src={product.image} alt={product.name} />
              ) : (
                <span className="pos-product-card__image-placeholder">Sin imagen</span>
              )}
            </div>
            <div className="pos-product-card__name">{product.name}</div>
            <div className="pos-product-card__sku">{product.sku ?? "—"}</div>
            <div className="pos-product-card__price">
              {Intl.NumberFormat().format(product.price)}
            </div>
            <div className="pos-product-card__stock">Stock: {product.stock ?? "—"}</div>
            <div className="pos-product-card__availability" title={availabilitySummary}>
              {availability ? (
                <>
                  <span className="pos-product-card__availability-label">Sucursales:</span>
                  <span className="pos-product-card__availability-values">
                    {availabilitySummary}
                  </span>
                </>
              ) : availabilityLoading ? (
                <span className="pos-product-card__availability-placeholder">
                  Consultando existencias…
                </span>
              ) : (
                <span className="pos-product-card__availability-placeholder">
                  Sin datos corporativos
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
