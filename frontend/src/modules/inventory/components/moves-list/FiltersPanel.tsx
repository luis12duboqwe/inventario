import React from "react";

type MoveType = "IN" | "OUT" | "TRANSFER" | "ADJUST";
type MoveStatus = "DRAFT" | "PENDING" | "APPROVED" | "PARTIAL" | "DONE" | "CANCELLED";

export type MoveFilters = {
  query?: string;
  type?: MoveType;
  status?: MoveStatus;
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
        onChange={(event) => {
          const next: MoveFilters = { ...v };
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
        value={v.type || "ALL"}
        onChange={(event) => {
          const selected = event.target.value as MoveType | "ALL";
          const next: MoveFilters = { ...v };
          if (selected === "ALL") {
            delete next.type;
          } else {
            next.type = selected;
          }
          onChange(next);
        }}
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
        onChange={(event) => {
          const selected = event.target.value as MoveStatus | "ALL";
          const next: MoveFilters = { ...v };
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
        <option value="PENDING">Pendiente</option>
        <option value="APPROVED">Aprobado</option>
        <option value="PARTIAL">Parcial</option>
        <option value="DONE">Completado</option>
        <option value="CANCELLED">Cancelado</option>
      </select>
      <input
        placeholder="Origen ID"
        value={v.sourceId || ""}
        onChange={(event) => {
          const next: MoveFilters = { ...v };
          const value = event.target.value.trim();
          if (value) {
            next.sourceId = value;
          } else {
            delete next.sourceId;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        placeholder="Destino ID"
        value={v.destId || ""}
        onChange={(event) => {
          const next: MoveFilters = { ...v };
          const value = event.target.value.trim();
          if (value) {
            next.destId = value;
          } else {
            delete next.destId;
          }
          onChange(next);
        }}
        style={{ padding: 8, borderRadius: 8 }}
      />
      <input
        type="date"
        value={v.dateFrom || ""}
        onChange={(event) => {
          const next: MoveFilters = { ...v };
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
          const next: MoveFilters = { ...v };
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
    </div>
  );
}
