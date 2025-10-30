import React from "react";
// [PACK23-CUSTOMERS-LIST-IMPORTS-START]
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SalesCustomers } from "../../../services/sales";
import type { Customer, CustomerListParams } from "../../../services/sales";
// [PACK23-CUSTOMERS-LIST-IMPORTS-END]
import { CustomersFiltersBar, CustomersTable } from "../components/customers";
// [PACK26-CUSTOMERS-PERMS-START]
import { useAuthz, PERMS, RequirePerm } from "../../../auth/useAuthz";
// [PACK26-CUSTOMERS-PERMS-END]

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

  // [PACK23-CUSTOMERS-LIST-FETCH-START]
  async function fetchCustomers(extra?: Partial<CustomerListParams>) {
    if (!canList) {
      setItems([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await SalesCustomers.listCustomers({ page, pageSize, q, tier, tag, ...extra });
      setItems(res.items || []);
      setTotal(res.total || 0);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { fetchCustomers(); }, [page, pageSize, tier, tag, q, canList]);
  // [PACK23-CUSTOMERS-LIST-FETCH-END]

  const rows: CustomerRow[] = items.map((customer) => ({
    id: String(customer.id),
    name: customer.name,
    phone: customer.phone,
    email: customer.email,
    tier: customer.tier,
    lastSale: customer.lastSaleAt ? new Date(customer.lastSaleAt).toLocaleDateString() : "—",
  }));

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {/* [PACK26-CUSTOMERS-LIST-GUARD-START] */}
      {!canList ? (
        <div>No autorizado</div>
      ) : (
        <>
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
          <RequirePerm perm={PERMS.CUSTOMER_CREATE} fallback={null}>
            <div>
              <button
                style={{ padding: "6px 10px", borderRadius: 8 }}
                onClick={() => navigate("/sales/customers/new")}
              >
                Nuevo cliente
              </button>
            </div>
          </RequirePerm>
          <CustomersTable
            rows={rows}
            onRowClick={(row) => navigate(`/sales/customers/${row.id}`)}
          />
          <div style={{ color: "#9ca3af", fontSize: 12 }}>
            {loading ? "Cargando clientes…" : `${total} clientes encontrados`}
          </div>
        </>
      )}
      {/* [PACK26-CUSTOMERS-LIST-GUARD-END] */}
    </div>
  );
}
