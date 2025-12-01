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
    <div style={{ display: "grid", gridTemplateColumns: "2fr repeat(4, 1fr) auto", gap: 8 }}>
      <input
        placeholder="Cliente o #pedido"
  value={filters.query ?? ""}
  onChange={(event) => handleChange("query", event.target.value)}
        style={{ padding: 8, borderRadius: 8, background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(148, 163, 184, 0.25)", color: "#f8fafc" }}
      />
      <select
        value={filters.type ?? "ALL"}
        onChange={(event) => handleChange("type", event.target.value as PaymentFilters["type"])}
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Tipo</option>
        <option value="PAYMENT">Cobro</option>
        <option value="REFUND">Reembolso</option>
        <option value="CREDIT_NOTE">Nota crédito</option>
      </select>
      <select
        value={filters.method ?? "ALL"}
        onChange={(event) => handleChange("method", event.target.value as PaymentFilters["method"])}
        style={{ padding: 8, borderRadius: 8 }}
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
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
  value={filters.dateTo ?? ""}
  onChange={(event) => handleChange("dateTo", event.target.value)}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <button onClick={onNewPayment} style={{ padding: "8px 12px", borderRadius: 8, background: "#38bdf8", color: "#0b1220", border: 0 }}>
        Nuevo cobro
      </button>
    </div>
  );
}

export type { PaymentFilters, PaymentsFiltersBarProps };
export default PaymentsFiltersBar;
