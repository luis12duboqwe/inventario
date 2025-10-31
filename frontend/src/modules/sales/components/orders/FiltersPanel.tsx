import React from "react";

export type OrderFilters = {
  query?: string;
  status?: "DRAFT" | "OPEN" | "PAID" | "CANCELLED" | "REFUNDED" | "ALL";
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
        onChange={(event) => onChange({ ...v, query: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={v.status || "ALL"}
        onChange={(event) =>
          onChange({ ...v, status: event.target.value as OrderFilters["status"] })
        }
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
        onChange={(event) => onChange({ ...v, storeId: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateFrom || ""}
        onChange={(event) => onChange({ ...v, dateFrom: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateTo || ""}
        onChange={(event) => onChange({ ...v, dateTo: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <div />
    </div>
  );
}

export default FiltersPanel;
