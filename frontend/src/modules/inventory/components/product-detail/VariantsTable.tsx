import React from "react";

type Variant = {
  id: string;
  sku: string;
  attrs: string;
  price: number;
  stock: number;
};

type Props = {
  items?: Variant[];
};

export default function VariantsTable({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ color: "#9ca3af", padding: 12 }}>Sin variantes</div>;
  }

  return (
    <div style={{ overflow: "auto", borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead>
          <tr style={{ background: "rgba(255,255,255,0.03)" }}>
            <th style={{ textAlign: "left", padding: 10 }}>SKU</th>
            <th style={{ textAlign: "left", padding: 10 }}>Atributos</th>
            <th style={{ textAlign: "right", padding: 10 }}>Precio</th>
            <th style={{ textAlign: "center", padding: 10 }}>Stock</th>
          </tr>
        </thead>
        <tbody>
          {data.map((variant) => (
            <tr key={variant.id}>
              <td style={{ padding: 10 }}>{variant.sku}</td>
              <td style={{ padding: 10 }}>{variant.attrs}</td>
              <td style={{ padding: 10, textAlign: "right" }}>{Intl.NumberFormat().format(variant.price)}</td>
              <td style={{ padding: 10, textAlign: "center" }}>{variant.stock}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
