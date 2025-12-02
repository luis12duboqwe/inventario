import React from "react";

type PaymentMethod = "CASH" | "CARD" | "TRANSFER" | "MIXED";

type PaymentMethodSelectorProps = {
  method: PaymentMethod;
  onChange: (method: PaymentMethod) => void;
};

const METHODS: PaymentMethod[] = ["CASH", "CARD", "TRANSFER", "MIXED"];

function PaymentMethodSelector({ method, onChange }: PaymentMethodSelectorProps) {
  return (
    <div className="payment-method-selector">
      {METHODS.map((option) => {
        const isActive = method === option;
        return (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={`payment-method-button ${isActive ? "payment-method-button-active" : ""}`}
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
