import React, { useState } from "react";
import { FiltersBar, SidePanel, SummaryCards, Table } from "../components/common";

type ReturnRow = {
  date: string;
  number: string;
  reason: string;
  items: number;
  total: number;
};

const columns = [
  { key: "date", label: "Fecha" },
  { key: "number", label: "#RET" },
  { key: "reason", label: "Motivo" },
  { key: "items", label: "Ítems", align: "center" as const },
  { key: "total", label: "Crédito", align: "right" as const },
];

export function ReturnsListPage() {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [rows] = useState<ReturnRow[]>([]); // TODO(wire)
  const [selectedRow, setSelectedRow] = useState<ReturnRow | null>(null);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <SummaryCards
        items={[
          { label: "Devoluciones hoy", value: "—" },
          { label: "Crédito total", value: "—" },
        ]}
      />
      <FiltersBar>
        <input
          placeholder="#RET/Cliente/IMEI"
          onChange={(event) => setFilters({ ...filters, q: event.target.value })}
          style={{ padding: 8, borderRadius: 8 }}
        />
        <input
          type="date"
          onChange={(event) => setFilters({ ...filters, dateFrom: event.target.value })}
          style={{ padding: 8, borderRadius: 8 }}
        />
        <input
          type="date"
          onChange={(event) => setFilters({ ...filters, dateTo: event.target.value })}
          style={{ padding: 8, borderRadius: 8 }}
        />
      </FiltersBar>
      <Table cols={columns} rows={rows} onRowClick={(row) => setSelectedRow(row as ReturnRow)} />
      <SidePanel
        title="Devolución"
        rows={
          selectedRow
            ? [
                ["Fecha", selectedRow.date],
                ["#RET", selectedRow.number],
                ["Motivo", selectedRow.reason],
                ["Crédito", selectedRow.total],
              ]
            : []
        }
        onClose={() => setSelectedRow(null)}
      />
    </div>
  );
}
