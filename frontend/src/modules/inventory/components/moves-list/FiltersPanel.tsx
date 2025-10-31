import React from "react";

export type MoveFilters = {
  query?: string;
  type?: "IN" | "OUT" | "TRANSFER" | "ADJUST" | "ALL";
  status?:
    | "DRAFT"
    | "PENDING"
    | "APPROVED"
    | "PARTIAL"
    | "DONE"
    | "CANCELLED"
    | "ALL";
  sourceId?: string;
  destId?: string;
  dateFrom?: string;
  dateTo?: string;
};

type Props = {
  value: MoveFilters;
  onChange: (next: MoveFilters) => void;
};

export default function FiltersPanel({ value, onChange }: Props) {
  const v = value || {};

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr 1fr",
        gap: 8,
      }}
    >
      <input
        placeholder="Buscar (#mov, referencia)"
        value={v.query || ""}
        onChange={(event) => onChange({ ...v, query: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <select
        value={v.type || "ALL"}
        onChange={(event) =>
          onChange({ ...v, type: event.target.value as MoveFilters["type"] })
        }
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Todos</option>
        <option value="IN">Ingreso</option>
        <option value="OUT">Salida</option>
        <option value="TRANSFER">Transferencia</option>
        <option value="ADJUST">Ajuste</option>
      </select>
      <select
        value={v.status || "ALL"}
        onChange={(event) =>
          onChange({
            ...v,
            status: event.target.value as MoveFilters["status"],
          })
        }
        style={{ padding: 8, borderRadius: 8 }}
      >
        <option value="ALL">Todos</option>
        <option value="DRAFT">Borrador</option>
        <option value="PENDING">Pendiente</option>
        <option value="APPROVED">Aprobado</option>
        <option value="PARTIAL">Parcial</option>
        <option value="DONE">Completado</option>
        <option value="CANCELLED">Cancelado</option>
      </select>
      <input
        placeholder="Origen ID"
        value={v.sourceId || ""}
        onChange={(event) => onChange({ ...v, sourceId: event.target.value })}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Destino ID"
        value={v.destId || ""}
        onChange={(event) => onChange({ ...v, destId: event.target.value })}
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
    </div>
  );
}
