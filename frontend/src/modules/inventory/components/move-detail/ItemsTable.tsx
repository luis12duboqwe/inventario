import React from "react";

type Item = {
  id: string;
  sku: string;
  name: string;
  qty: number;
  cost?: number;
};

type Props = {
  items?: Item[];
};

export default function ItemsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (!data.length) {
    return <div className="p-3 text-muted-foreground">Sin items</div>;
  }

  return (
    <div className="overflow-auto rounded-xl border border-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-surface-highlight">
            <th className="text-left p-2.5">SKU</th>
            <th className="text-left p-2.5">Producto</th>
            <th className="text-center p-2.5">Cant.</th>
            <th className="text-right p-2.5">Costo</th>
            <th className="text-right p-2.5">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => {
            const subtotal = (row.qty || 0) * (row.cost || 0);
            return (
              <tr key={row.id}>
                <td className="p-2.5">{row.sku}</td>
                <td className="p-2.5">{row.name}</td>
                <td className="p-2.5 text-center">{row.qty}</td>
                <td className="p-2.5 text-right">{Intl.NumberFormat().format(row.cost || 0)}</td>
                <td className="p-2.5 text-right">{Intl.NumberFormat().format(subtotal)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
