import React from "react";

export type OrderFilters = {
  query?: string;
  status?: "DRAFT" | "OPEN" | "COMPLETED" | "CANCELLED" | "ALL";
  payment?: "UNPAID" | "PARTIAL" | "PAID" | "REFUNDED" | "ALL";
  channel?: "POS" | "WEB" | "MANUAL" | "ALL";
  dateFrom?: string;
  dateTo?: string;
};

export type OrdersFiltersBarProps = {
  value: OrderFilters;
  onChange: (next: OrderFilters) => void;
};

function FiltersBar({ value, onChange }: OrdersFiltersBarProps) {
  const nextValue = value ?? {};

  const changeQuery = (raw: string) => {
    const trimmed = raw.trim();
    const next: OrderFilters = { ...nextValue };
    if (trimmed) {
      next.query = trimmed;
    } else {
      delete next.query;
    }
    onChange(next);
  };

  const changeStatus = (status: OrderFilters["status"]) => {
    const next: OrderFilters = { ...nextValue };
    if (!status || status === "ALL") {
      delete next.status;
    } else {
      next.status = status;
    }
    onChange(next);
  };

  const changePayment = (payment: OrderFilters["payment"]) => {
    const next: OrderFilters = { ...nextValue };
    if (!payment || payment === "ALL") {
      delete next.payment;
    } else {
      next.payment = payment;
    }
    onChange(next);
  };

  const changeChannel = (channel: OrderFilters["channel"]) => {
    const next: OrderFilters = { ...nextValue };
    if (!channel || channel === "ALL") {
      delete next.channel;
    } else {
      next.channel = channel;
    }
    onChange(next);
  };

  const changeDate = (key: "dateFrom" | "dateTo", raw: string) => {
    const next: OrderFilters = { ...nextValue };
    const trimmed = raw.trim();
    if (trimmed) {
      next[key] = trimmed;
    } else {
      delete next[key];
    }
    onChange(next);
  };

  return (
    <div className="orders-list-filters-bar">
      <input
        placeholder="Buscar (cliente o #pedido)"
        value={nextValue.query ?? ""}
        onChange={(event) => changeQuery(event.target.value)}
        className="orders-list-filters-input"
      />
      <select
        value={nextValue.status ?? "ALL"}
        onChange={(event) => changeStatus(event.target.value as OrderFilters["status"])}
        className="orders-list-filters-input"
      >
        <option value="ALL">Todos</option>
        <option value="DRAFT">Borrador</option>
        <option value="OPEN">Abierto</option>
        <option value="COMPLETED">Completado</option>
        <option value="CANCELLED">Cancelado</option>
      </select>
      <select
        value={nextValue.payment ?? "ALL"}
        onChange={(event) => changePayment(event.target.value as OrderFilters["payment"])}
        className="orders-list-filters-input"
      >
        <option value="ALL">Pago</option>
        <option value="UNPAID">No pagado</option>
        <option value="PARTIAL">Parcial</option>
        <option value="PAID">Pagado</option>
        <option value="REFUNDED">Reembolsado</option>
      </select>
      <select
        value={nextValue.channel ?? "ALL"}
        onChange={(event) => changeChannel(event.target.value as OrderFilters["channel"])}
        className="orders-list-filters-input"
      >
        <option value="ALL">Canal</option>
        <option value="POS">POS</option>
        <option value="WEB">Web</option>
        <option value="MANUAL">Manual</option>
      </select>
      <input
        type="date"
        value={nextValue.dateFrom ?? ""}
        onChange={(event) => changeDate("dateFrom", event.target.value)}
        className="orders-list-filters-input"
      />
      <input
        type="date"
        value={nextValue.dateTo ?? ""}
        onChange={(event) => changeDate("dateTo", event.target.value)}
        className="orders-list-filters-input"
      />
    </div>
  );
}

export default FiltersBar;
