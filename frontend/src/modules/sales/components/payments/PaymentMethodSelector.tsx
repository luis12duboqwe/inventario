import React from "react";

type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "MIXED";

type PaymentMethodSelectorProps = {
  method: PaymentMethod;
  onChange: (method: PaymentMethod) => void;
};

const METHODS: PaymentMethod[] = ["CASH", "CARD", "TRANSFER", "MIXED"];

function PaymentMethodSelector({ method, onChange }: PaymentMethodSelectorProps) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {METHODS.map((option) => {
        const isActive = method === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              background: isActive ? "#2563eb" : "rgba(148, 163, 184, 0.16)",
              color: "#f8fafc",
              border: "1px solid rgba(37, 99, 235, 0.4)",
            }}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

export type { PaymentMethod, PaymentMethodSelectorProps };
export default PaymentMethodSelector;
