export type Credentials = {
  username: string;
  password: string;
};

export type Store = {
  id: number;
  name: string;
  location?: string | null;
  timezone: string;
};

export type Role = {
  id: number;
  name: string;
};

export type UserAccount = {
  id: number;
  username: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
  roles: Role[];
};

export type Device = {
  id: number;
  sku: string;
  name: string;
  quantity: number;
  store_id: number;
  unit_price: number;
  inventory_value: number;
  imei?: string | null;
  serial?: string | null;
  marca?: string | null;
  modelo?: string | null;
  color?: string | null;
  capacidad_gb?: number | null;
  estado_comercial?: "nuevo" | "A" | "B" | "C";
  proveedor?: string | null;
  costo_unitario?: number;
  margen_porcentaje?: number;
  garantia_meses?: number;
  lote?: string | null;
  fecha_compra?: string | null;
};

export type CatalogDevice = Device & { store_name: string };

export type PaymentMethod = "EFECTIVO" | "TARJETA" | "TRANSFERENCIA" | "OTRO" | "CREDITO";

export type ContactHistoryEntry = {
  timestamp: string;
  note: string;
};

export type Customer = {
  id: number;
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
  outstanding_debt: number;
  history: ContactHistoryEntry[];
  last_interaction_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerPayload = {
  name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  address?: string;
  notes?: string;
  outstanding_debt?: number;
  history?: ContactHistoryEntry[];
};

export type Supplier = {
  id: number;
  name: string;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
  outstanding_debt: number;
  history: ContactHistoryEntry[];
  created_at: string;
  updated_at: string;
};

export type SupplierPayload = {
  name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  address?: string;
  notes?: string;
  outstanding_debt?: number;
  history?: ContactHistoryEntry[];
};

export type RepairOrderPart = {
  id: number;
  repair_order_id: number;
  device_id: number;
  quantity: number;
  unit_cost: number;
};

export type RepairOrder = {
  id: number;
  store_id: number;
  customer_id?: number | null;
  customer_name?: string | null;
  technician_name: string;
  damage_type: string;
  device_description?: string | null;
  notes?: string | null;
  status: "PENDIENTE" | "EN_PROCESO" | "LISTO" | "ENTREGADO";
  labor_cost: number;
  parts_cost: number;
  total_cost: number;
  inventory_adjusted: boolean;
  opened_at: string;
  updated_at: string;
  delivered_at?: string | null;
  parts: RepairOrderPart[];
  status_color: string;
};

export type RepairOrderPayload = {
  store_id: number;
  customer_id?: number | null;
  customer_name?: string | null;
  technician_name: string;
  damage_type: string;
  device_description?: string;
  notes?: string;
  labor_cost?: number;
  parts?: { device_id: number; quantity: number; unit_cost?: number }[];
};

export type RepairOrderUpdatePayload = Partial<RepairOrderPayload> & {
  status?: RepairOrder["status"];
};

export type CashSession = {
  id: number;
  store_id: number;
  status: "ABIERTO" | "CERRADO";
  opening_amount: number;
  closing_amount: number;
  expected_amount: number;
  difference_amount: number;
  payment_breakdown: Record<string, number>;
  notes?: string | null;
  opened_by_id?: number | null;
  closed_by_id?: number | null;
  opened_at: string;
  closed_at?: string | null;
};

export type SaleItem = {
  id: number;
  sale_id: number;
  device_id: number;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  total_line: number;
};

export type SaleReturn = {
  id: number;
  sale_id: number;
  device_id: number;
  quantity: number;
  reason: string;
  processed_by_id?: number | null;
  created_at: string;
};

export type Sale = {
  id: number;
  store_id: number;
  customer_id?: number | null;
  customer_name?: string | null;
  payment_method: PaymentMethod;
  discount_percent: number;
  subtotal_amount: number;
  tax_amount: number;
  total_amount: number;
  notes?: string | null;
  created_at: string;
  performed_by_id?: number | null;
  cash_session_id?: number | null;
  customer?: Customer | null;
  cash_session?: CashSession | null;
  items: SaleItem[];
  returns: SaleReturn[];
};

export type SaleCreateInput = {
  store_id: number;
  payment_method: PaymentMethod;
  items: { device_id: number; quantity: number; discount_percent?: number }[];
  discount_percent?: number;
  customer_id?: number;
  customer_name?: string;
  notes?: string;
};

export type SaleReturnInput = {
  sale_id: number;
  items: { device_id: number; quantity: number; reason: string }[];
};

export type PurchaseOrderItem = {
  id: number;
  purchase_order_id: number;
  device_id: number;
  quantity_ordered: number;
  quantity_received: number;
  unit_cost: number;
};

export type PurchaseOrder = {
  id: number;
  store_id: number;
  supplier: string;
  status: "PENDIENTE" | "PARCIAL" | "COMPLETADA" | "CANCELADA";
  notes?: string | null;
  created_at: string;
  updated_at: string;
  created_by_id?: number | null;
  closed_at?: string | null;
  items: PurchaseOrderItem[];
};

export type PurchaseOrderCreateInput = {
  store_id: number;
  supplier: string;
  items: { device_id: number; quantity_ordered: number; unit_cost: number }[];
  notes?: string;
};

export type PurchaseReceiveInput = {
  items: { device_id: number; quantity: number }[];
};

export type PurchaseReturnInput = {
  device_id: number;
  quantity: number;
  reason: string;
};

export type PosCartItemInput = {
  device_id: number;
  quantity: number;
  discount_percent?: number;
};

export type PaymentBreakdown = Partial<Record<PaymentMethod, number>>;

export type PosSalePayload = {
  store_id: number;
  payment_method: PaymentMethod;
  items: PosCartItemInput[];
  discount_percent?: number;
  customer_id?: number;
  customer_name?: string;
  notes?: string;
  confirm?: boolean;
  save_as_draft?: boolean;
  draft_id?: number | null;
  apply_taxes?: boolean;
  cash_session_id?: number | null;
  payment_breakdown?: PaymentBreakdown;
};

export type PosDraft = {
  id: number;
  store_id: number;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type PosSaleResponse = {
  status: "draft" | "registered";
  sale?: Sale | null;
  draft?: PosDraft | null;
  receipt_url?: string | null;
  warnings: string[];
  cash_session_id?: number | null;
  payment_breakdown?: PaymentBreakdown;
};

export type PosConfig = {
  store_id: number;
  tax_rate: number;
  invoice_prefix: string;
  printer_name?: string | null;
  printer_profile?: string | null;
  quick_product_ids: number[];
  updated_at: string;
};

export type PosConfigUpdateInput = {
  store_id: number;
  tax_rate: number;
  invoice_prefix: string;
  printer_name?: string | null;
  printer_profile?: string | null;
  quick_product_ids: number[];
};

export type DeviceSearchFilters = {
  imei?: string;
  serial?: string;
  capacidad_gb?: number;
  color?: string;
  marca?: string;
  modelo?: string;
};

export type MovementInput = {
  device_id: number;
  movement_type: "entrada" | "salida" | "ajuste";
  quantity: number;
  reason?: string;
};

export type Summary = {
  store_id: number;
  store_name: string;
  total_items: number;
  total_value: number;
  devices: Device[];
};

export type StoreMembership = {
  id: number;
  user_id: number;
  store_id: number;
  can_create_transfer: boolean;
  can_receive_transfer: boolean;
  created_at: string;
};

export type StoreMembershipInput = {
  user_id: number;
  store_id: number;
  can_create_transfer: boolean;
  can_receive_transfer: boolean;
};

export type TransferOrderItem = {
  id: number;
  transfer_order_id: number;
  device_id: number;
  quantity: number;
};

export type TransferOrder = {
  id: number;
  origin_store_id: number;
  destination_store_id: number;
  status: "SOLICITADA" | "EN_TRANSITO" | "RECIBIDA" | "CANCELADA";
  reason?: string | null;
  created_at: string;
  updated_at: string;
  dispatched_at?: string | null;
  received_at?: string | null;
  cancelled_at?: string | null;
  items: TransferOrderItem[];
};

export type TransferOrderInput = {
  origin_store_id: number;
  destination_store_id: number;
  reason?: string;
  items: { device_id: number; quantity: number }[];
};

export type TransferTransitionInput = {
  reason?: string;
};

export type StoreValueMetric = {
  store_id: number;
  store_name: string;
  device_count: number;
  total_units: number;
  total_value: number;
};

export type LowStockDevice = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  inventory_value: number;
};

export type DashboardPoint = {
  label: string;
  value: number;
};

export type InventoryMetrics = {
  totals: {
    stores: number;
    devices: number;
    total_units: number;
    total_value: number;
  };
  top_stores: StoreValueMetric[];
  low_stock_devices: LowStockDevice[];
  global_performance: {
    total_sales: number;
    sales_count: number;
    total_stock: number;
    open_repairs: number;
    gross_profit: number;
  };
  sales_trend: DashboardPoint[];
  stock_breakdown: DashboardPoint[];
  repair_mix: DashboardPoint[];
  profit_breakdown: DashboardPoint[];
};

export type AuditLogEntry = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: string | null;
  performed_by_id?: number | null;
  created_at: string;
};

export type RotationMetric = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  name: string;
  sold_units: number;
  received_units: number;
  rotation_rate: number;
};

export type AnalyticsRotation = {
  items: RotationMetric[];
};

export type AgingMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_id: number;
  store_name: string;
  days_in_stock: number;
  quantity: number;
};

export type AnalyticsAging = {
  items: AgingMetric[];
};

export type StockoutForecastMetric = {
  device_id: number;
  sku: string;
  name: string;
  store_name: string;
  average_daily_sales: number;
  projected_days: number | null;
  quantity: number;
};

export type AnalyticsForecast = {
  items: StockoutForecastMetric[];
};

export type StoreComparativeMetric = {
  store_id: number;
  store_name: string;
  device_count: number;
  total_units: number;
  inventory_value: number;
  average_rotation: number;
  average_aging_days: number;
  sales_last_30_days: number;
  sales_count_last_30_days: number;
};

export type AnalyticsComparative = {
  items: StoreComparativeMetric[];
};

export type ProfitMarginMetric = {
  store_id: number;
  store_name: string;
  revenue: number;
  cost: number;
  profit: number;
  margin_percent: number;
};

export type AnalyticsProfitMargin = {
  items: ProfitMarginMetric[];
};

export type SalesProjectionMetric = {
  store_id: number;
  store_name: string;
  average_daily_units: number;
  average_ticket: number;
  projected_units: number;
  projected_revenue: number;
  confidence: number;
};

export type AnalyticsSalesProjection = {
  items: SalesProjectionMetric[];
};

export type TOTPStatus = {
  is_active: boolean;
  activated_at?: string | null;
  last_verified_at?: string | null;
};

export type TOTPSetup = {
  secret: string;
  otpauth_url: string;
};

export type ActiveSession = {
  id: number;
  user_id: number;
  session_token: string;
  created_at: string;
  last_used_at?: string | null;
  revoked_at?: string | null;
  revoked_by_id?: number | null;
  revoke_reason?: string | null;
};

export type SessionRevokeInput = {
  reason: string;
};

export type SyncOutboxStatus = "PENDING" | "SENT" | "FAILED";

export type SyncOutboxEntry = {
  id: number;
  entity_type: string;
  entity_id: string;
  operation: string;
  payload: Record<string, unknown>;
  attempt_count: number;
  last_attempt_at?: string | null;
  status: SyncOutboxStatus;
  priority: "HIGH" | "NORMAL" | "LOW";
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type SyncOutboxStatsEntry = {
  entity_type: string;
  priority: "HIGH" | "NORMAL" | "LOW";
  total: number;
  pending: number;
  failed: number;
  latest_update?: string | null;
  oldest_pending?: string | null;
};

export type SyncSessionCompact = {
  id: number;
  mode: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  error_message?: string | null;
};

export type SyncStoreHistory = {
  store_id: number | null;
  store_name: string;
  sessions: SyncSessionCompact[];
};

export type BackupJob = {
  id: number;
  mode: "automatico" | "manual";
  executed_at: string;
  pdf_path: string;
  archive_path: string;
  total_size_bytes: number;
  notes?: string | null;
};

export type ReleaseInfo = {
  version: string;
  release_date: string;
  notes: string;
  download_url: string;
};

export type UpdateStatus = {
  current_version: string;
  latest_version: string | null;
  is_update_available: boolean;
  latest_release: ReleaseInfo | null;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

function buildStoreQuery(storeIds?: number[]): string {
  if (!storeIds || storeIds.length === 0) {
    return "";
  }
  const params = storeIds.map((id) => `store_ids=${encodeURIComponent(id)}`).join("&");
  return `?${params}`;
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Error ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.blob()) as unknown as T;
}

export async function login(credentials: Credentials): Promise<{ access_token: string }> {
  const params = new URLSearchParams();
  params.append("username", credentials.username);
  params.append("password", credentials.password);

  const response = await fetch(`${API_URL}/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: params,
  });

  if (!response.ok) {
    throw new Error("Credenciales inválidas");
  }

  return (await response.json()) as { access_token: string };
}

export function getCurrentUser(token: string): Promise<UserAccount> {
  return request<UserAccount>("/auth/me", { method: "GET" }, token);
}

export function listUsers(token: string): Promise<UserAccount[]> {
  return request<UserAccount[]>("/users", { method: "GET" }, token);
}

export function listRoles(token: string): Promise<Role[]> {
  return request<Role[]>("/users/roles", { method: "GET" }, token);
}

export function updateUserRoles(token: string, userId: number, roles: string[], reason: string): Promise<UserAccount> {
  return request<UserAccount>(
    `/users/${userId}/roles`,
    { method: "PUT", body: JSON.stringify({ roles }), headers: { "X-Reason": reason } },
    token
  );
}

export function updateUserStatus(token: string, userId: number, isActive: boolean, reason: string): Promise<UserAccount> {
  return request<UserAccount>(
    `/users/${userId}`,
    { method: "PATCH", body: JSON.stringify({ is_active: isActive }), headers: { "X-Reason": reason } },
    token
  );
}

export function getStores(token: string): Promise<Store[]> {
  return request<Store[]>("/stores", { method: "GET" }, token);
}

export function getSummary(token: string): Promise<Summary[]> {
  return request<Summary[]>("/inventory/summary", { method: "GET" }, token);
}

export function getDevices(token: string, storeId: number): Promise<Device[]> {
  return request<Device[]>(`/stores/${storeId}/devices`, { method: "GET" }, token);
}

export function listPurchaseOrders(token: string, storeId: number, limit = 50): Promise<PurchaseOrder[]> {
  const params = new URLSearchParams({ limit: String(limit), store_id: String(storeId) });
  return request<PurchaseOrder[]>(`/purchases/?${params.toString()}`, { method: "GET" }, token);
}

export function createPurchaseOrder(
  token: string,
  payload: PurchaseOrderCreateInput,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    "/purchases",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function receivePurchaseOrder(
  token: string,
  orderId: number,
  payload: PurchaseReceiveInput,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    `/purchases/${orderId}/receive`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function cancelPurchaseOrder(
  token: string,
  orderId: number,
  reason: string
): Promise<PurchaseOrder> {
  return request<PurchaseOrder>(
    `/purchases/${orderId}/cancel`,
    {
      method: "POST",
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function registerPurchaseReturn(
  token: string,
  orderId: number,
  payload: PurchaseReturnInput,
  reason: string
): Promise<void> {
  return request<void>(
    `/purchases/${orderId}/returns`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function listCustomers(
  token: string,
  query?: string,
  limit = 100
): Promise<Customer[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (query) {
    params.append("q", query);
  }
  return request<Customer[]>(`/customers?${params.toString()}`, { method: "GET" }, token);
}

export function exportCustomersCsv(token: string, query?: string): Promise<Blob> {
  const params = new URLSearchParams({ export: "csv" });
  if (query) {
    params.append("q", query);
  }
  return request<Blob>(`/customers?${params.toString()}`, { method: "GET" }, token);
}

export function createCustomer(
  token: string,
  payload: CustomerPayload,
  reason: string
): Promise<Customer> {
  return request<Customer>(
    "/customers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateCustomer(
  token: string,
  customerId: number,
  payload: Partial<CustomerPayload>,
  reason: string
): Promise<Customer> {
  return request<Customer>(
    `/customers/${customerId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteCustomer(token: string, customerId: number, reason: string): Promise<void> {
  return request<void>(
    `/customers/${customerId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export function listSuppliers(
  token: string,
  query?: string,
  limit = 100
): Promise<Supplier[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (query) {
    params.append("q", query);
  }
  return request<Supplier[]>(`/suppliers?${params.toString()}`, { method: "GET" }, token);
}

export function exportSuppliersCsv(token: string, query?: string): Promise<Blob> {
  const params = new URLSearchParams({ export: "csv" });
  if (query) {
    params.append("q", query);
  }
  return request<Blob>(`/suppliers?${params.toString()}`, { method: "GET" }, token);
}

export function createSupplier(
  token: string,
  payload: SupplierPayload,
  reason: string
): Promise<Supplier> {
  return request<Supplier>(
    "/suppliers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateSupplier(
  token: string,
  supplierId: number,
  payload: Partial<SupplierPayload>,
  reason: string
): Promise<Supplier> {
  return request<Supplier>(
    `/suppliers/${supplierId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteSupplier(token: string, supplierId: number, reason: string): Promise<void> {
  return request<void>(
    `/suppliers/${supplierId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export function listRepairOrders(
  token: string,
  params: { store_id?: number; status?: string; q?: string; limit?: number }
): Promise<RepairOrder[]> {
  const searchParams = new URLSearchParams();
  if (params.store_id) {
    searchParams.append("store_id", String(params.store_id));
  }
  if (params.status) {
    searchParams.append("status", params.status);
  }
  if (params.q) {
    searchParams.append("q", params.q);
  }
  if (params.limit) {
    searchParams.append("limit", String(params.limit));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return request<RepairOrder[]>(`/repairs${suffix}`, { method: "GET" }, token);
}

export function createRepairOrder(
  token: string,
  payload: RepairOrderPayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    "/repairs",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateRepairOrder(
  token: string,
  repairId: number,
  payload: RepairOrderUpdatePayload,
  reason: string
): Promise<RepairOrder> {
  return request<RepairOrder>(
    `/repairs/${repairId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteRepairOrder(token: string, repairId: number, reason: string): Promise<void> {
  return request<void>(
    `/repairs/${repairId}`,
    { method: "DELETE", headers: { "X-Reason": reason } },
    token
  );
}

export async function downloadRepairOrderPdf(token: string, repairId: number): Promise<Blob> {
  return request<Blob>(`/repairs/${repairId}/pdf`, { method: "GET" }, token);
}

export function searchCatalogDevices(
  token: string,
  filters: DeviceSearchFilters
): Promise<CatalogDevice[]> {
  const params = new URLSearchParams();
  if (filters.imei) params.append("imei", filters.imei);
  if (filters.serial) params.append("serial", filters.serial);
  if (typeof filters.capacidad_gb === "number") params.append("capacidad_gb", String(filters.capacidad_gb));
  if (filters.color) params.append("color", filters.color);
  if (filters.marca) params.append("marca", filters.marca);
  if (filters.modelo) params.append("modelo", filters.modelo);
  const query = params.toString();
  const path = query ? `/inventory/devices/search?${query}` : "/inventory/devices/search";
  return request<CatalogDevice[]>(path, { method: "GET" }, token);
}

export function registerMovement(
  token: string,
  storeId: number,
  payload: MovementInput,
  reason: string
) {
  return request(`/inventory/stores/${storeId}/movements`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "X-Reason": reason },
  }, token);
}

export function listSales(token: string, storeId?: number, limit = 50): Promise<Sale[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (typeof storeId === "number") {
    params.append("store_id", String(storeId));
  }
  const query = params.toString();
  const path = query ? `/sales?${query}` : "/sales";
  return request<Sale[]>(path, { method: "GET" }, token);
}

export function createSale(
  token: string,
  payload: SaleCreateInput,
  reason: string
): Promise<Sale> {
  return request<Sale>(
    "/sales",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function registerSaleReturn(
  token: string,
  payload: SaleReturnInput,
  reason: string
): Promise<SaleReturn[]> {
  return request<SaleReturn[]>(
    "/sales/returns",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function listStoreMemberships(token: string, storeId: number): Promise<StoreMembership[]> {
  return request(`/stores/${storeId}/memberships`, { method: "GET" }, token);
}

export function upsertStoreMembership(
  token: string,
  storeId: number,
  userId: number,
  payload: StoreMembershipInput
): Promise<StoreMembership> {
  return request(`/stores/${storeId}/memberships/${userId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  }, token);
}

export function listTransfers(token: string, storeId?: number): Promise<TransferOrder[]> {
  const query = typeof storeId === "number" ? `?store_id=${storeId}` : "";
  const path = query ? `/transfers/${query}` : "/transfers";
  return request(path, { method: "GET" }, token);
}

export function createTransferOrder(
  token: string,
  payload: TransferOrderInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    "/transfers",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function dispatchTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    `/transfers/${transferId}/dispatch`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function receiveTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    `/transfers/${transferId}/receive`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function cancelTransferOrder(
  token: string,
  transferId: number,
  payload: TransferTransitionInput,
  reason: string
): Promise<TransferOrder> {
  return request(
    `/transfers/${transferId}/cancel`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function triggerSync(token: string, storeId?: number) {
  return request(`/sync/run`, {
    method: "POST",
    body: JSON.stringify({ store_id: storeId ?? null }),
  }, token);
}

export function runBackup(token: string, note?: string): Promise<BackupJob> {
  return request<BackupJob>("/backups/run", {
    method: "POST",
    body: JSON.stringify({ nota: note }),
  }, token);
}

export function fetchBackupHistory(token: string): Promise<BackupJob[]> {
  return request<BackupJob[]>("/backups/history", { method: "GET" }, token);
}

export async function downloadInventoryPdf(token: string): Promise<void> {
  const response = await fetch(`${API_URL}/reports/inventory/pdf`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_inventario.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getUpdateStatus(token: string): Promise<UpdateStatus> {
  return request<UpdateStatus>("/updates/status", { method: "GET" }, token);
}

export function getReleaseHistory(token: string, limit = 10): Promise<ReleaseInfo[]> {
  return request<ReleaseInfo[]>(`/updates/history?limit=${limit}`, { method: "GET" }, token);
}

export function getInventoryMetrics(token: string, lowStockThreshold = 5): Promise<InventoryMetrics> {
  return request<InventoryMetrics>(
    `/reports/metrics?low_stock_threshold=${lowStockThreshold}`,
    { method: "GET" },
    token
  );
}

export function getRotationAnalytics(token: string, storeIds?: number[]): Promise<AnalyticsRotation> {
  const query = buildStoreQuery(storeIds);
  return request<AnalyticsRotation>(`/reports/analytics/rotation${query}`, { method: "GET" }, token);
}

export function getAgingAnalytics(token: string, storeIds?: number[]): Promise<AnalyticsAging> {
  const query = buildStoreQuery(storeIds);
  return request<AnalyticsAging>(`/reports/analytics/aging${query}`, { method: "GET" }, token);
}

export function getForecastAnalytics(token: string, storeIds?: number[]): Promise<AnalyticsForecast> {
  const query = buildStoreQuery(storeIds);
  return request<AnalyticsForecast>(`/reports/analytics/stockout_forecast${query}`, { method: "GET" }, token);
}

export async function downloadAnalyticsPdf(token: string, storeIds?: number[]): Promise<void> {
  const query = buildStoreQuery(storeIds);
  const response = await fetch(`${API_URL}/reports/analytics/pdf${query}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF analítico");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_analytics.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadAnalyticsCsv(token: string, storeIds?: number[]): Promise<void> {
  const query = buildStoreQuery(storeIds);
  const response = await fetch(`${API_URL}/reports/analytics/export.csv${query}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el CSV analítico");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_analytics.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getComparativeAnalytics(token: string, storeIds?: number[]): Promise<AnalyticsComparative> {
  const query = buildStoreQuery(storeIds);
  return request<AnalyticsComparative>(`/reports/analytics/comparative${query}`, { method: "GET" }, token);
}

export function getProfitMarginAnalytics(token: string, storeIds?: number[]): Promise<AnalyticsProfitMargin> {
  const query = buildStoreQuery(storeIds);
  return request<AnalyticsProfitMargin>(`/reports/analytics/profit_margin${query}`, { method: "GET" }, token);
}

export function getSalesProjectionAnalytics(
  token: string,
  storeIds?: number[],
): Promise<AnalyticsSalesProjection> {
  const query = buildStoreQuery(storeIds);
  return request<AnalyticsSalesProjection>(`/reports/analytics/sales_forecast${query}`, { method: "GET" }, token);
}

export function getTotpStatus(token: string): Promise<TOTPStatus> {
  return request<TOTPStatus>("/security/2fa/status", { method: "GET" }, token);
}

export function setupTotp(token: string, reason: string): Promise<TOTPSetup> {
  return request<TOTPSetup>(
    "/security/2fa/setup",
    { method: "POST", headers: { "X-Reason": reason } },
    token
  );
}

export function activateTotp(token: string, code: string, reason: string): Promise<TOTPStatus> {
  return request<TOTPStatus>(
    "/security/2fa/activate",
    { method: "POST", body: JSON.stringify({ code }), headers: { "X-Reason": reason } },
    token
  );
}

export function disableTotp(token: string, reason: string): Promise<void> {
  return request<void>(
    "/security/2fa/disable",
    { method: "POST", headers: { "X-Reason": reason } },
    token
  );
}

export function listActiveSessions(token: string, userId?: number): Promise<ActiveSession[]> {
  const query = userId ? `?user_id=${userId}` : "";
  return request<ActiveSession[]>(`/security/sessions${query}`, { method: "GET" }, token);
}

export function revokeSession(token: string, sessionId: number, reason: string): Promise<ActiveSession> {
  return request<ActiveSession>(
    `/security/sessions/${sessionId}/revoke`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function listSyncOutbox(token: string, statusFilter?: SyncOutboxStatus): Promise<SyncOutboxEntry[]> {
  const query = statusFilter ? `?status_filter=${statusFilter}` : "";
  return request<SyncOutboxEntry[]>(`/sync/outbox${query}`, { method: "GET" }, token);
}

export function retrySyncOutbox(token: string, ids: number[], reason: string): Promise<SyncOutboxEntry[]> {
  return request<SyncOutboxEntry[]>(
    "/sync/outbox/retry",
    {
      method: "POST",
      body: JSON.stringify({ ids }),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function getSyncOutboxStats(token: string): Promise<SyncOutboxStatsEntry[]> {
  return request<SyncOutboxStatsEntry[]>("/sync/outbox/stats", { method: "GET" }, token);
}

export function getSyncHistory(token: string, limitPerStore = 5): Promise<SyncStoreHistory[]> {
  return request<SyncStoreHistory[]>(
    `/sync/history?limit_per_store=${limitPerStore}`,
    { method: "GET" },
    token,
  );
}

export function getAuditLogs(token: string, limit = 100, action?: string): Promise<AuditLogEntry[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (action) {
    params.append("action", action);
  }
  return request<AuditLogEntry[]>(`/audit/logs?${params.toString()}`, { method: "GET" }, token);
}

export function submitPosSale(
  token: string,
  payload: PosSalePayload,
  reason: string
): Promise<PosSaleResponse> {
  return request<PosSaleResponse>(
    "/pos/sale",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function getPosConfig(token: string, storeId: number): Promise<PosConfig> {
  return request<PosConfig>(`/pos/config?store_id=${storeId}`, { method: "GET" }, token);
}

export function updatePosConfig(
  token: string,
  payload: PosConfigUpdateInput,
  reason: string
): Promise<PosConfig> {
  return request<PosConfig>(
    "/pos/config",
    {
      method: "PUT",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function openCashSession(
  token: string,
  payload: { store_id: number; opening_amount: number; notes?: string },
  reason: string
): Promise<CashSession> {
  return request<CashSession>(
    "/pos/cash/open",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function closeCashSession(
  token: string,
  payload: { session_id: number; closing_amount: number; payment_breakdown?: Record<string, number>; notes?: string },
  reason: string
): Promise<CashSession> {
  return request<CashSession>(
    "/pos/cash/close",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listCashSessions(
  token: string,
  storeId: number,
  limit = 30
): Promise<CashSession[]> {
  const params = new URLSearchParams({ store_id: String(storeId), limit: String(limit) });
  return request<CashSession[]>(`/pos/cash/history?${params.toString()}`, { method: "GET" }, token);
}

export async function downloadPosReceipt(token: string, saleId: number): Promise<Blob> {
  const response = await fetch(`${API_URL}/pos/receipt/${saleId}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error("No fue posible obtener el recibo del punto de venta");
  }
  return await response.blob();
}
