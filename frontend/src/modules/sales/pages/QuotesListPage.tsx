import React, { useState } from "react";
import { FiltersBar, SidePanel, SummaryCards, Table } from "../components/common";

const columns = [
  { key: "date", label: "Fecha" },
  { key: "number", label: "#Q" },
  { key: "customer", label: "Cliente" },
  { key: "items", label: "Ítems", align: "center" as const },
  { key: "total", label: "Total", align: "right" as const },
];

type QuoteRow = {
  date: string;
  number: string;
  customer: string;
  items: number;
  total: number;
};

export function QuotesListPage() {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [rows] = useState<QuoteRow[]>([]); // TODO(wire)
  const [selectedRow, setSelectedRow] = useState<QuoteRow | null>(null);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <SummaryCards
        items={[
          { label: "Cotizaciones hoy", value: "—" },
          { label: "Convertidas", value: "—" },
          { label: "Pendientes", value: "—" },
        ]}
      />
      <FiltersBar>
        <input
          placeholder="#Q/Cliente"
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
      <Table cols={columns} rows={rows} onRowClick={(row) => setSelectedRow(row as QuoteRow)} />
      <SidePanel
        title="Cotización"
        rows={
          selectedRow
            ? [
                ["Fecha", selectedRow.date],
                ["#Q", selectedRow.number],
                ["Cliente", selectedRow.customer],
                ["Total", selectedRow.total],
              ]
            : []
        }
        onClose={() => setSelectedRow(null)}
      />
    </div>
  );
}
