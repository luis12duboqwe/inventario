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

  const handleChange = (patch: Partial<OrderFilters>) => {
    onChange({ ...nextValue, ...patch });
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
        onChange={(event) => handleChange({ query: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={nextValue.status ?? "ALL"}
        onChange={(event) => handleChange({ status: event.target.value as OrderFilters["status"] })}
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
        onChange={(event) => handleChange({ payment: event.target.value as OrderFilters["payment"] })}
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
        onChange={(event) => handleChange({ channel: event.target.value as OrderFilters["channel"] })}
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
        onChange={(event) => handleChange({ dateFrom: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={nextValue.dateTo ?? ""}
        onChange={(event) => handleChange({ dateTo: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
    </div>
  );
}

export default FiltersBar;
