import React from "react";

type Props = {
  steps: string[];
  active: number;
};

export default function Stepper({ steps, active }: Props) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {steps.map((step, index) => (
        <div
          key={`${step}-${index}`}
          style={{
            padding: "6px 10px",
            borderRadius: 999,
            background: index === active ? "#2563eb" : "rgba(255,255,255,0.08)",
            color: "#fff",
            fontSize: 12,
          }}
        >
          {index + 1}. {step}
        </div>
      ))}
    </div>
  );
}
