import React from "react";

export type Customer = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
};

type Props = {
  customer?: Customer | null;
  onPick?: () => void;
  onClear?: () => void;
};

export default function CustomerPicker({ customer, onPick, onClear }: Props) {
  return (
    <div className="pos-customer-picker">
      <div className="pos-customer-picker-info">
        <div className="pos-customer-picker-label">Cliente</div>
        {customer ? (
          <div className="pos-customer-picker-details">
            <strong>{customer.name}</strong>
            <span className="pos-customer-picker-contact">
              {customer.phone || customer.email || ""}
            </span>
          </div>
        ) : (
          <div className="pos-customer-picker-empty">Sin cliente</div>
        )}
      </div>
      <button onClick={onPick} className="pos-customer-picker-select-btn">
        Seleccionar
      </button>
      {customer ? (
        <button onClick={onClear} className="pos-customer-picker-clear-btn">
          Quitar
        </button>
      ) : null}
    </div>
  );
}
