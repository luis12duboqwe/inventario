import React from "react";

export type POSPaymentMethod = "CASH" | "CARD" | "MIXED";

export type POSPaymentMethodsProps = {
  method: POSPaymentMethod;
  onChange: (method: POSPaymentMethod) => void;
};

const METHODS: POSPaymentMethod[] = ["CASH", "CARD", "MIXED"];

function PaymentMethods({ method, onChange }: POSPaymentMethodsProps) {
  return (
    <div className="pos-payment-methods">
      {METHODS.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          className={method === option ? "pos-payment-method-btn-active" : "pos-payment-method-btn"}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

export default PaymentMethods;
