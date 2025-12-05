import React from "react";
// [PACK23-CUSTOMERS-LIST-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { emitClientError } from "../../../utils/clientLog";
import { SalesCustomers } from "../../../services/sales";
import type { Customer, CustomerListParams } from "../../../services/sales";
// [PACK23-CUSTOMERS-LIST-IMPORTS-END]
import { CustomersFiltersBar, CustomersTable } from "../components/customers";
// [PACK26-CUSTOMERS-PERMS-START]
import { useAuthz, PERMS, RequirePerm } from "../../../auth/useAuthz";
// [PACK26-CUSTOMERS-PERMS-END]
// [PACK27-INJECT-EXPORT-CUSTOMERS-START]
import ExportDropdown from "@/components/ExportDropdown";
// [PACK27-INJECT-EXPORT-CUSTOMERS-END]
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@components/ui/Skeleton";
// [PACK25-SKELETON-USE-END]
import { readQueue } from "@/services/offline";
import { flushOffline } from "../utils/offline";

type CustomerRow = {
  id: string;
  name: string;
  phone?: string | undefined;
  email?: string | undefined;
  tier?: string | undefined;
  lastSale?: string | undefined;
};

export function CustomersListPage() {
  const navigate = useNavigate();
  const { can } = useAuthz();
  const canList = can(PERMS.CUSTOMER_LIST);
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
  const fetchCustomers = useCallback(
    async (extra?: Partial<CustomerListParams>) => {
      if (!canList) {
        setItems([]);
        setTotal(0);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const params: CustomerListParams = { page, pageSize };

        const trimmedQ = q.trim();
        if (trimmedQ) {
          params.q = trimmedQ;
        }
        if (tier && tier.trim()) {
          params.tier = tier.trim();
        }
        if (tag && tag.trim()) {
          params.tag = tag.trim();
        }

        if (extra) {
          if (typeof extra.page === "number") {
            params.page = extra.page;
          }
          if (extra.q !== undefined) params.q = extra.q;
          if (extra.tier !== undefined) params.tier = extra.tier;
          if (extra.tag !== undefined) params.tag = extra.tag;
        }

        const response = await SalesCustomers.listCustomers(params);
        setItems(response.items);
        setTotal(response.total);
      } catch (err) {
        emitClientError("CustomersListPage", "Error loading customers", err);
        pushToast("Error al cargar clientes", "error");
      } finally {
        setLoading(false);
      }
    },
    [canList, page, pageSize, q, tier, tag],
  );

  useEffect(() => {
    void fetchCustomers();
  }, [fetchCustomers]);

  useEffect(() => {
    setPendingOffline(readQueue().length);
  }, []);

  const handleFlush = useCallback(async () => {
    setFlushing(true);
    setFlushMessage(null);
    try {
      await flushOffline();
      setFlushMessage("Sincronización completada");
      setPendingOffline(readQueue().length);
      void fetchCustomers();
    } catch {
      setFlushMessage("Error al sincronizar");
    } finally {
      setFlushing(false);
    }
  }, [fetchCustomers]);

  const rows: CustomerRow[] = useMemo(() => {
    return items.map((item) => ({
      id: String(item.id),
      name: item.name,
      phone: item.phone,
      email: item.email,
      tier: item.tier,
      lastSale: item.lastSaleAt,
    }));
  }, [items]);

  const handleRowClick = useCallback(
    (row: CustomerRow) => {
      navigate(`/sales/customers/${row.id}`);
    },
    [navigate],
  );

  return (
    <div data-testid="customers-list" className="customers-list-container">
      {/* [PACK26-CUSTOMERS-LIST-GUARD-START] */}
      {canList ? (
        <>
          <div className="customers-list-actions">
            <RequirePerm perm={PERMS.CUSTOMER_CREATE}>
              <button
                className="customers-list-button customers-list-button-primary"
                onClick={() => navigate("/sales/customers/new")}
              >
                Nuevo cliente
              </button>
            </RequirePerm>
          </div>
          <div className="customers-list-filters-container">
            <div className="customers-list-filters-wrapper">
              <CustomersFiltersBar
                value={{
                  query: filters.query ?? "",
                  tag: filters.tag ?? "",
                  tier: filters.tier ?? "",
                }}
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

          {pendingOffline > 0 ? (
            <div className="customers-list-offline-bar">
              <span className="customers-list-offline-text">
                Pendientes offline: {pendingOffline}
              </span>
              <button
                type="button"
                onClick={handleFlush}
                disabled={flushing}
                className="customers-list-button customers-list-button-secondary customers-list-retry-btn"
              >
                {flushing ? "Reintentando…" : "Reintentar pendientes"}
              </button>
            </div>
          ) : null}
          {flushMessage ? <div className="customers-list-flush-message">{flushMessage}</div> : null}
          {loading ? (
            <Skeleton lines={8} />
          ) : (
            <CustomersTable rows={rows} onRowClick={handleRowClick} />
          )}
          <div className="customers-list-total-text">
            {loading ? "Cargando clientes…" : `${total} clientes encontrados`}
          </div>
        </>
      ) : null}
      {/* [PACK26-CUSTOMERS-LIST-GUARD-END] */}
    </div>
  );
}
export default CustomersListPage;
