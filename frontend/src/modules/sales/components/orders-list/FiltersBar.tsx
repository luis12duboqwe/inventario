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
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "2fr repeat(4, 1fr) 1.1fr",
        gap: 8,
      }}
    >
      <input
        placeholder="Buscar (cliente o #pedido)"
        value={nextValue.query ?? ""}
        onChange={(event) => changeQuery(event.target.value)}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={nextValue.status ?? "ALL"}
        onChange={(event) => changeStatus(event.target.value as OrderFilters["status"])}
        style={{ padding: 8, borderRadius: 8 }}
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
        style={{ padding: 8, borderRadius: 8 }}
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
        style={{ padding: 8, borderRadius: 8 }}
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
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={nextValue.dateTo ?? ""}
        onChange={(event) => changeDate("dateTo", event.target.value)}
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}

export default FiltersBar;
