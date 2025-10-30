import React from "react";
// [PACK23-CUSTOMERS-LIST-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SalesCustomers } from "../../../services/sales";
import type { Customer, CustomerListParams } from "../../../services/sales";
// [PACK23-CUSTOMERS-LIST-IMPORTS-END]
import { CustomersFiltersBar, CustomersTable } from "../components/customers";
// [PACK27-INJECT-EXPORT-CUSTOMERS-START]
import ExportDropdown from "@/components/ExportDropdown";
// [PACK27-INJECT-EXPORT-CUSTOMERS-END]
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@/ui/Skeleton";
// [PACK25-SKELETON-USE-END]
import { readQueue } from "@/services/offline";
import { flushOffline } from "../utils/offline";

type CustomerRow = {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  tier?: string;
  lastSale?: string;
};

export function CustomersListPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Record<string, string>>({});
  // [PACK23-CUSTOMERS-LIST-STATE-START]
  const [items, setItems] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [q, setQ] = useState("");
  const [tier, setTier] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  // [PACK23-CUSTOMERS-LIST-STATE-END]
  const [tag, setTag] = useState<string | undefined>(undefined);
  const [pendingOffline, setPendingOffline] = useState(0);
  const [flushing, setFlushing] = useState(false);
  const [flushMessage, setFlushMessage] = useState<string | null>(null);

  // [PACK23-CUSTOMERS-LIST-FETCH-START]
  async function fetchCustomers(extra?: Partial<CustomerListParams>) {
    setLoading(true);
    try {
      const res = await SalesCustomers.listCustomers({ page, pageSize, q, tier, tag, ...extra });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { fetchCustomers(); }, [page, pageSize, tier, tag, q]);
  // [PACK23-CUSTOMERS-LIST-FETCH-END]

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, [items]);

  const rows: CustomerRow[] = useMemo(
    () =>
      items.map((customer) => ({
        id: String(customer.id),
        name: customer.name,
        phone: customer.phone,
        email: customer.email,
        tier: customer.tier,
        lastSale: customer.lastSaleAt ? new Date(customer.lastSaleAt).toLocaleDateString() : "—",
      })),
    [items],
  );

  const handleRowClick = useCallback(
    (row: CustomerRow) => {
      navigate(`/sales/customers/${row.id}`);
    },
    [navigate],
  );

  const handleFlush = useCallback(async () => {
    setFlushing(true);
    try {
      const result = await flushOffline();
      setPendingOffline(result.pending);
      setFlushMessage(`Reintentadas: ${result.flushed}. Pendientes: ${result.pending}.`);
    } catch (error) {
      setFlushMessage("No fue posible sincronizar. Intenta más tarde.");
    } finally {
      setFlushing(false);
    }
  }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ flex: "1 1 320px" }}>
          <CustomersFiltersBar
            value={{ query: filters.query ?? "", tag: filters.tag ?? "", tier: filters.tier ?? "" }}
            onChange={(value) => {
              setFilters({
                query: value.query ?? "",
                tag: value.tag ?? "",
                tier: value.tier ?? "",
              });
              setQ(value.query ?? "");
              setTier(value.tier ? value.tier : undefined);
              setTag(value.tag ? value.tag : undefined);
              setPage(1);
            }}
          />
        </div>
        <ExportDropdown entity="customers" currentItems={items} />
      </div>
      <CustomersTable
        rows={rows}
        onRowClick={(row) => navigate(`/sales/customers/${row.id}`)}
      />
      />
      {pendingOffline > 0 ? (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ color: "#fbbf24" }}>Pendientes offline: {pendingOffline}</span>
          <button
            type="button"
            onClick={handleFlush}
            disabled={flushing}
            style={{ padding: "6px 12px", borderRadius: 8, border: "none", background: "rgba(56,189,248,0.16)", color: "#e0f2fe" }}
          >
            {flushing ? "Reintentando…" : "Reintentar pendientes"}
          </button>
        </div>
      ) : null}
      {flushMessage ? <div style={{ color: "#9ca3af", fontSize: 12 }}>{flushMessage}</div> : null}
      {loading ? <Skeleton lines={8} /> : (
        <CustomersTable
          rows={rows}
          onRowClick={handleRowClick}
        />
      )}
      <div style={{ color: "#9ca3af", fontSize: 12 }}>
        {loading ? "Cargando clientes…" : `${total} clientes encontrados`}
      </div>
    </div>
  );
}
