import React from "react";

type Attribute = {
  key: string;
  value: string;
};

type Props = {
  items?: Attribute[];
};

export default function Attributes({ items }: Props) {
  const data = Array.isArray(items) ? items : [];

  if (data.length === 0) {
    return <div style={{ color: "#9ca3af" }}>Sin atributos</div>;
  }

  return (
    <div style={{ display: "grid", gap: 6 }}>
      {data.map((attribute, index) => (
        <div
          key={`${attribute.key}-${index}`}
          style={{
            display: "flex",
            justifyContent: "space-between",
            borderBottom: "1px dashed rgba(255,255,255,0.08)",
            padding: "6px 0",
          }}
        >
          <span style={{ color: "#94a3b8" }}>{attribute.key}</span>
          <span>{attribute.value}</span>
        </div>
      ))}
    </div>
  );
}
