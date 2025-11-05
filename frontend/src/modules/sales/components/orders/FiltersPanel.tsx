import React from "react";

type OrderStatusFilter = "DRAFT" | "OPEN" | "PAID" | "CANCELLED" | "REFUNDED";

export type OrderFilters = {
  query?: string;
  status?: OrderStatusFilter;
  storeId?: string;
  dateFrom?: string;
  dateTo?: string;
};

type Props = {
  value: OrderFilters;
  onChange: (next: OrderFilters) => void;
};

function FiltersPanel({ value, onChange }: Props) {
  const v = value || {};
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(6, minmax(160px, 1fr))",
        gap: 8,
      }}
    >
      <input
        placeholder="Buscar (cliente, #factura, ref)"
        value={v.query || ""}
        onChange={(event) => {
          const next: OrderFilters = { ...v };
          const value = event.target.value;
          if (value) {
            next.query = value;
          } else {
            delete next.query;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={v.status || "ALL"}
        onChange={(event) => {
          const selected = event.target.value as OrderStatusFilter | "ALL";
          const next: OrderFilters = { ...v };
          if (selected === "ALL") {
            delete next.status;
          } else {
            next.status = selected;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Todos</option>
        <option value="DRAFT">Borrador</option>
        <option value="OPEN">Abierto</option>
        <option value="PAID">Pagado</option>
        <option value="CANCELLED">Cancelado</option>
        <option value="REFUNDED">Reembolsado</option>
      </select>
      <input
        placeholder="Sucursal ID"
        value={v.storeId || ""}
        onChange={(event) => {
          const next: OrderFilters = { ...v };
          const value = event.target.value.trim();
          if (value) {
            next.storeId = value;
          } else {
            delete next.storeId;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateFrom || ""}
        onChange={(event) => {
          const next: OrderFilters = { ...v };
          const value = event.target.value;
          if (value) {
            next.dateFrom = value;
          } else {
            delete next.dateFrom;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateTo || ""}
        onChange={(event) => {
          const next: OrderFilters = { ...v };
          const value = event.target.value;
          if (value) {
            next.dateTo = value;
          } else {
            delete next.dateTo;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <div />
    </div>
  );
}

export default FiltersPanel;
