import React from "react";

type Props = {
  left: React.ReactNode;
  right: React.ReactNode;
};

export default function Layout({ left, right }: Props) {
  return (
    <div className="pos-layout">
      <div className="pos-layout__column">{left}</div>
      <div className="pos-layout__column">{right}</div>
    </div>
  );
}
