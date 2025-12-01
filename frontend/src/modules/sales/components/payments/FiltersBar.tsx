import React from "react";

type PaymentFilters = {
  query?: string;
  method?: "ALL" | "CASH" | "CARD" | "TRANSFER" | "MIXED";
  dateFrom?: string;
  dateTo?: string;
  type?: "ALL" | "PAYMENT" | "REFUND" | "CREDIT_NOTE";
};

type PaymentsFiltersBarProps = {
  value: PaymentFilters;
  onChange: (value: PaymentFilters) => void;
  onNewPayment?: () => void;
};

function PaymentsFiltersBar({ value, onChange, onNewPayment }: PaymentsFiltersBarProps) {
  const filters = value ?? {};

  const handleChange = <K extends keyof PaymentFilters>(key: K, val: PaymentFilters[K]) => {
    const next = { ...filters } as PaymentFilters;
    const isEmptyString = typeof val === "string" && val.trim() === "";
    const isAllOption = (key === "type" || key === "method") && val === "ALL";
    if (val === undefined || val === null || isEmptyString || isAllOption) {
      delete next[key];
    } else {
      next[key] = val;
    }
    onChange(next);
  };

  return (
    <div className="payments-filters-bar">
      <input
        placeholder="Cliente o #pedido"
        value={filters.query ?? ""}
        onChange={(event) => handleChange("query", event.target.value)}
        className="payments-filters-input"
      />
      <select
        value={filters.type ?? "ALL"}
        onChange={(event) => handleChange("type", event.target.value as PaymentFilters["type"])}
        className="payments-filters-select"
      >
        <option value="ALL">Tipo</option>
        <option value="PAYMENT">Cobro</option>
        <option value="REFUND">Reembolso</option>
        <option value="CREDIT_NOTE">Nota crédito</option>
      </select>
      <select
        value={filters.method ?? "ALL"}
        onChange={(event) => handleChange("method", event.target.value as PaymentFilters["method"])}
        className="payments-filters-select"
      >
        <option value="ALL">Método</option>
        <option value="CASH">Efectivo</option>
        <option value="CARD">Tarjeta</option>
        <option value="TRANSFER">Transferencia</option>
        <option value="MIXED">Mixto</option>
      </select>
      <input
        type="date"
        value={filters.dateFrom ?? ""}
        onChange={(event) => handleChange("dateFrom", event.target.value)}
        className="payments-filters-date"
      />
      <input
        type="date"
        value={filters.dateTo ?? ""}
        onChange={(event) => handleChange("dateTo", event.target.value)}
        className="payments-filters-date"
      />
      <button onClick={onNewPayment} className="payments-filters-btn">
        Nuevo cobro
      </button>
    </div>
  );
}

export type { PaymentFilters, PaymentsFiltersBarProps };
export default PaymentsFiltersBar;
