import React from "react";

export type POSCustomer = {
  id: string;
  name: string;
  phone?: string;
};

export type POSCustomerSelectorProps = {
  customer?: POSCustomer | null;
  onPick?: () => void;
  onCreate?: () => void;
};

function CustomerSelector({ customer, onPick, onCreate }: POSCustomerSelectorProps) {
  return (
    <div className="pos-customer-selector">
      <span className="pos-customer-selector-label">Cliente</span>
      {customer ? (
        <div className="pos-customer-card">
          <div className="pos-customer-info">
            <strong>{customer.name}</strong>
            <div className="pos-customer-phone">{customer.phone ?? ""}</div>
          </div>
          <button onClick={onPick} className="pos-customer-btn-change">
            Cambiar
          </button>
        </div>
      ) : (
        <div className="pos-customer-actions">
          <button onClick={onPick} className="pos-customer-btn">
            Seleccionar
          </button>
          <button onClick={onCreate} className="pos-customer-btn">
            Nuevo
          </button>
        </div>
      )}
    </div>
  );
}

export default CustomerSelector;
