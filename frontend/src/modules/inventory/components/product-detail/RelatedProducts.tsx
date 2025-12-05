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
    return <div className="text-muted-foreground">Sin relacionados</div>;
  }

  return (
    <div className="grid gap-2">
      {data.map((product) => (
        <button
          key={product.id}
          onClick={() => onOpen?.(product.id)}
          className="text-left p-2 rounded-lg border border-border bg-surface-highlight hover:bg-surface-highlight/80"
        >
          {product.name}
        </button>
      ))}
    </div>
  );
}
