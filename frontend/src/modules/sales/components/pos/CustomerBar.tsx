import React from "react";

type Customer = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  docId?: string;
  tier?: string;
};

type Props = {
  customer?: Customer | null;
  onPick?: () => void;
  onQuickNew?: () => void;
};

export default function CustomerBar({ customer, onPick, onQuickNew }: Props) {
  return (
    <div className="pos-customer-bar">
      <div className="pos-customer-info">
        <div className="pos-customer-label">Cliente</div>
        <div className="pos-customer-name">{customer?.name ?? "Mostrador"}</div>
        {!!customer?.phone && <div className="pos-customer-phone">{customer.phone}</div>}
        {!!customer?.docId && <div className="pos-customer-doc">RTN: {customer.docId}</div>}
      </div>
      <button onClick={onPick} className="pos-customer-button">
        Buscar
      </button>
      <button onClick={onQuickNew} className="pos-customer-button">
        Nuevo
      </button>
    </div>
  );
}
