import React from "react";

export default function FiltersBar({
  children,
}: {
  children?: React.ReactNode;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(6, 1fr)",
        gap: 8,
      }}
    >
      {children}
    </div>
  );
}
