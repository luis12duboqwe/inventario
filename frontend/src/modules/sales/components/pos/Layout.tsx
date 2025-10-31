import React from "react";

type Props = {
  left: React.ReactNode;
  right: React.ReactNode;
};

export default function Layout({ left, right }: Props) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1.6fr 1fr",
        gap: 12,
        alignItems: "start",
      }}
    >
      <div>{left}</div>
      <div>{right}</div>
    </div>
  );
}
