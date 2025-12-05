import React from "react";

type Variant = {
  id: string;
  sku: string;
  attrs: string;
  price: number;
  stock: number;
  minimumStock: number;
  reorderPoint: number;
};

type Props = {
  items?: Variant[];
};

export default function VariantsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div className="p-3 text-muted-foreground">Sin variantes</div>;
  }

  return (
    <div className="overflow-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-surface-highlight">
            <th className="text-left p-2.5">SKU</th>
            <th className="text-left p-2.5">Atributos</th>
            <th className="text-right p-2.5">Precio</th>
            <th className="text-center p-2.5">Stock</th>
            <th className="text-center p-2.5">Mínimo</th>
            <th className="text-center p-2.5">Reorden</th>
          </tr>
        </thead>
        <tbody>
          {data.map((variant) => (
            <tr key={variant.id}>
              <td className="p-2.5">{variant.sku}</td>
              <td className="p-2.5">{variant.attrs}</td>
              <td className="p-2.5 text-right">{Intl.NumberFormat().format(variant.price)}</td>
              <td className="p-2.5 text-center">{variant.stock}</td>
              <td
                className={`p-2.5 text-center ${
                  variant.stock <= variant.minimumStock ? "text-red-400" : "text-sky-400"
                }`}
              >
                {variant.minimumStock}
              </td>
              <td
                className={`p-2.5 text-center ${
                  variant.stock <= variant.reorderPoint ? "text-yellow-400" : "text-sky-400"
                }`}
              >
                {variant.reorderPoint}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
