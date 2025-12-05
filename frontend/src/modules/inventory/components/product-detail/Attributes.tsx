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
    return <div className="text-muted-foreground">Sin atributos</div>;
  }

  return (
    <div className="grid gap-2">
      {data.map((attribute, index) => (
        <div
          key={`${attribute.key}-${index}`}
          className="flex justify-between border-b border-dashed border-border py-1.5 last:border-0"
        >
          <span className="text-muted-foreground">{attribute.key}</span>
          <span>{attribute.value}</span>
        </div>
      ))}
    </div>
  );
}
