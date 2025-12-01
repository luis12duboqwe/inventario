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
    <div className="pos-quick-grid">
      {data.map((product) => (
        <button
          key={product.id}
          onClick={() => onPick?.(product.id)}
          className="pos-quick-grid-item"
        >
          <div className="pos-quick-grid-image-container">
            {product.imageUrl ? (
              <img src={product.imageUrl} alt={product.name} className="pos-quick-grid-image" />
            ) : (
              <span className="pos-quick-grid-no-image">Sin imagen</span>
            )}
          </div>
          <div className="pos-quick-grid-info">
            <span className="pos-quick-grid-name">{product.name}</span>
            <span className="pos-quick-grid-price">{currency.format(product.price)}</span>
          </div>
        </button>
      ))}
    </div>
  );
}

export default QuickGrid;
