import React from "react";

export type POSPaymentMethod = "CASH" | "CARD" | "MIXED";

export type POSPaymentMethodsProps = {
  method: POSPaymentMethod;
  onChange: (method: POSPaymentMethod) => void;
};

const METHODS: POSPaymentMethod[] = ["CASH", "CARD", "MIXED"];

function PaymentMethods({ method, onChange }: POSPaymentMethodsProps) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      {METHODS.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            background: method === option ? "#2563eb" : "rgba(255, 255, 255, 0.08)",
            color: "#fff",
            border: 0,
          }}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

export default PaymentMethods;
