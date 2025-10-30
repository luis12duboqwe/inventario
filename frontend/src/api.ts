import { getApiBaseUrl } from "./config/api";

export type Credentials = {
  username: string;
  password: string;
  // [PACK28-api]
  otp?: string;
};

// [PACK28-api]
export type AuthSession = {
  access_token: string;
  token_type: "bearer";
};

// [PACK28-api]
export type AuthProfile = {
  id: number;
  name: string;
  email?: string | null;
  role: string;
};

export type BootstrapStatus = {
  disponible: boolean;
  usuarios_registrados: number;
};

export type BootstrapRequest = {
  username: string;
  password: string;
  full_name?: string | null;
  telefono?: string | null;
};

export type Store = {
  id: number;
  name: string;
  location?: string | null;
  phone?: string | null;
  manager?: string | null;
  status: string;
  code: string;
  timezone: string;
  inventory_value: number;
  created_at: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  has_next: boolean;
};

export type Role = {
  id: number;
  name: string;
};

export type SystemLogLevel = "info" | "warning" | "error" | "critical";

export type UserAccount = {
  id: number;
  username: string;
  full_name?: string | null;
  telefono?: string | null;
  is_active: boolean;
  rol: string;
  estado: string;
  created_at: string;
  last_login_at?: string | null;
  locked_until?: string | null;
  failed_login_attempts?: number;
  roles: Role[];
  store_id?: number | null;
  store_name?: string | null;
};

export type UserQueryFilters = {
  search?: string;
  role?: string;
  status?: "all" | "active" | "inactive" | "locked";
  storeId?: number;
};

export type UserCreateInput = {
  username: string;
  password: string;
  full_name?: string | null;
  telefono?: string | null;
  roles: string[];
  store_id?: number | null;
};

export type UserUpdateInput = {
  full_name?: string | null;
  telefono?: string | null;
  password?: string | null;
  store_id?: number | null;
};

export type RoleModulePermission = {
  module: string;
  can_view: boolean;
  can_edit: boolean;
  can_delete: boolean;
};

export type RolePermissionMatrix = {
  role: string;
  permissions: RoleModulePermission[];
};

export type UserDashboardTotals = {
  total: number;
  active: number;
  inactive: number;
  locked: number;
};

export type UserDashboardActivity = {
  id: number;
  action: string;
  created_at: string;
  severity: "info" | "warning" | "critical";
  performed_by_id?: number | null;
  performed_by_name?: string | null;
  target_user_id?: number | null;
  target_username?: string | null;
  details?: Record<string, unknown> | null;
};

export type UserSessionSummary = {
  session_id: number;
  user_id: number;
  username: string;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  status: "activa" | "revocada" | "expirada";
  revoke_reason?: string | null;
};

export type UserDashboardMetrics = {
  generated_at: string;
  totals: UserDashboardTotals;
  recent_activity: UserDashboardActivity[];
  active_sessions: UserSessionSummary[];
  audit_alerts: DashboardAuditAlerts;
};

export type DeviceIdentifier = {
  id: number;
  producto_id: number;
  imei_1?: string | null;
  imei_2?: string | null;
  numero_serie?: string | null;
  estado_tecnico?: string | null;
  observaciones?: string | null;
};

export type DeviceIdentifierInput = {
  imei_1?: string | null;
  imei_2?: string | null;
  numero_serie?: string | null;
  estado_tecnico?: string | null;
  observaciones?: string | null;
};

export type Device = {
    id: number;
    sku: string;
    name: string;
  quantity: number;
  store_id: number;
  unit_price: number;
  inventory_value: number;
  completo: boolean;
  imei?: string | null;
  serial?: string | null;
  marca?: string | null;
  modelo?: string | null;
  categoria?: string | null;
  condicion?: string | null;
  color?: string | null;
  capacidad_gb?: number | null;
  capacidad?: string | null;
  estado_comercial?: "nuevo" | "A" | "B" | "C";
  estado?: string;
  proveedor?: string | null;
  costo_unitario?: number;
  costo_compra?: number;
  margen_porcentaje?: number;
  garantia_meses?: number;
  lote?: string | null;
  fecha_compra?: string | null;
  fecha_ingreso?: string | null;
  ubicacion?: string | null;
  descripcion?: string | null;
  imagen_url?: string | null;
  precio_venta?: number;
  identifier?: DeviceIdentifier | null;
};

export type CatalogDevice = Device & { store_name: string };

export type ImportValidation = {
  id: number;
  producto_id?: number | null;
  tipo: string;
  severidad: "advertencia" | "error" | string;
  descripcion: string;
  fecha: string;
  corregido: boolean;
};

export type ImportValidationDevice = {
  id: number;
  store_id: number;
  store_name: string;
  sku: string;
  name: string;
  imei?: string | null;
  serial?: string | null;
  marca?: string | null;
  modelo?: string | null;
};

export type ImportValidationDetail = ImportValidation & {
  device?: ImportValidationDevice | null;
};

export type ImportValidationSummary = {
  registros_revisados: number;
  advertencias: number;
  errores: number;
  campos_faltantes: string[];
  tiempo_total?: number | null;
};

export type DeviceUpdateInput = {
  name?: string | null;
  quantity?: number;
  unit_price?: number | null;
  imei?: string | null;
  serial?: string | null;
  marca?: string | null;
  modelo?: string | null;
  categoria?: string | null;
  condicion?: string | null;
  color?: string | null;
  capacidad_gb?: number | null;
  capacidad?: string | null;
  estado_comercial?: Device["estado_comercial"] | null;
  estado?: string | null;
  proveedor?: string | null;
  costo_unitario?: number | null;
  costo_compra?: number | null;
  margen_porcentaje?: number | null;
  garantia_meses?: number | null;
  lote?: string | null;
  fecha_compra?: string | null;
  fecha_ingreso?: string | null;
  ubicacion?: string | null;
  descripcion?: string | null;
  imagen_url?: string | null;
  precio_venta?: number | null;
  completo?: boolean;
};

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
  phone: string;
  address?: string | null;
  customer_type: string;
  status: string;
  credit_limit: number;
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
  phone: string;
  address?: string;
  customer_type?: string;
  status?: string;
  credit_limit?: number;
  notes?: string;
  outstanding_debt?: number;
  history?: ContactHistoryEntry[];
};

export type CustomerLedgerEntryType = "sale" | "payment" | "adjustment" | "note";

export type CustomerLedgerEntry = {
  id: number;
  entry_type: CustomerLedgerEntryType;
  reference_type?: string | null;
  reference_id?: string | null;
  amount: number;
  balance_after: number;
  note?: string | null;
  details: Record<string, unknown>;
  created_at: string;
  created_by?: string | null;
};

export type CustomerSaleSummary = {
  sale_id: number;
  store_id: number;
  store_name?: string | null;
  payment_method: PaymentMethod;
  status: string;
  subtotal_amount: number;
  tax_amount: number;
  total_amount: number;
  created_at: string;
};

export type CustomerInvoiceSummary = {
  sale_id: number;
  invoice_number: string;
  total_amount: number;
  status: string;
  created_at: string;
  store_id: number;
};

export type CustomerFinancialSnapshot = {
  credit_limit: number;
  outstanding_debt: number;
  available_credit: number;
  total_sales_credit: number;
  total_payments: number;
};

export type CustomerSummary = {
  customer: Customer;
  totals: CustomerFinancialSnapshot;
  sales: CustomerSaleSummary[];
  invoices: CustomerInvoiceSummary[];
  payments: CustomerLedgerEntry[];
  ledger: CustomerLedgerEntry[];
};

export type CustomerPortfolioItem = {
  customer_id: number;
  name: string;
  status: string;
  customer_type: string;
  credit_limit: number;
  outstanding_debt: number;
  available_credit: number;
  sales_total: number;
  sales_count: number;
  last_sale_at?: string | null;
  last_interaction_at?: string | null;
};

export type CustomerPortfolioTotals = {
  customers: number;
  moroso_flagged: number;
  outstanding_debt: number;
  sales_total: number;
};

export type CustomerPortfolioReport = {
  generated_at: string;
  category: "delinquent" | "frequent";
  filters: {
    category: "delinquent" | "frequent";
    date_from?: string | null;
    date_to?: string | null;
    limit: number;
  };
  items: CustomerPortfolioItem[];
  totals: CustomerPortfolioTotals;
};

export type CustomerLeaderboardEntry = {
  customer_id: number;
  name: string;
  status: string;
  customer_type: string;
  sales_total: number;
  sales_count: number;
  last_sale_at?: string | null;
  outstanding_debt: number;
};

export type CustomerDelinquentSummary = {
  customers_with_debt: number;
  moroso_flagged: number;
  total_outstanding_debt: number;
};

export type CustomerDashboardMetrics = {
  generated_at: string;
  months: number;
  new_customers_per_month: { label: string; value: number }[];
  top_customers: CustomerLeaderboardEntry[];
  delinquent_summary: CustomerDelinquentSummary;
};

export type CustomerPaymentPayload = {
  amount: number;
  method?: string;
  reference?: string | null;
  note?: string | null;
  sale_id?: number | null;
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

export type SupplierBatch = {
  id: number;
  supplier_id: number;
  store_id?: number | null;
  device_id?: number | null;
  model_name: string;
  batch_code: string;
  unit_cost: number;
  quantity: number;
  purchase_date: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type SupplierBatchPayload = {
  store_id?: number | null;
  device_id?: number | null;
  model_name: string;
  batch_code: string;
  unit_cost: number;
  quantity?: number;
  purchase_date: string;
  notes?: string | null;
};

export type SupplierBatchOverviewItem = {
  supplier_id: number;
  supplier_name: string;
  batch_count: number;
  total_quantity: number;
  total_value: number;
  latest_purchase_date: string;
  latest_batch_code?: string | null;
  latest_unit_cost?: number | null;
};

export type PurchaseVendor = {
  id_proveedor: number;
  nombre: string;
  telefono?: string | null;
  correo?: string | null;
  direccion?: string | null;
  tipo?: string | null;
  notas?: string | null;
  estado: string;
  total_compras: number;
  total_impuesto: number;
  compras_registradas: number;
  ultima_compra?: string | null;
};

export type PurchaseVendorPayload = {
  nombre: string;
  telefono?: string;
  correo?: string;
  direccion?: string;
  tipo?: string;
  notas?: string;
  estado?: string;
};

export type PurchaseVendorStatusPayload = {
  estado: string;
};

export type PurchaseRecordItem = {
  id_detalle: number;
  producto_id: number;
  cantidad: number;
  costo_unitario: number;
  subtotal: number;
  producto_nombre?: string | null;
};

export type PurchaseRecord = {
  id_compra: number;
  proveedor_id: number;
  proveedor_nombre: string;
  usuario_id: number;
  usuario_nombre?: string | null;
  fecha: string;
  forma_pago: string;
  estado: string;
  subtotal: number;
  impuesto: number;
  total: number;
  items: PurchaseRecordItem[];
};

export type PurchaseRecordItemPayload = {
  producto_id: number;
  cantidad: number;
  costo_unitario: number;
};

export type PurchaseRecordPayload = {
  proveedor_id: number;
  forma_pago: string;
  estado?: string;
  impuesto_tasa?: number;
  fecha?: string;
  items: PurchaseRecordItemPayload[];
};

export type PurchaseVendorHistory = {
  proveedor: PurchaseVendor;
  compras: PurchaseRecord[];
  total: number;
  impuesto: number;
  registros: number;
};

export type PurchaseVendorRanking = {
  vendor_id: number;
  vendor_name: string;
  total: number;
  orders: number;
};

export type PurchaseUserRanking = {
  user_id: number;
  user_name?: string | null;
  total: number;
  orders: number;
};

export type PurchaseStatistics = {
  updated_at: string;
  compras_registradas: number;
  total: number;
  impuesto: number;
  monthly_totals: { label: string; value: number }[];
  top_vendors: PurchaseVendorRanking[];
  top_users: PurchaseUserRanking[];
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

export type SaleDeviceSummary = {
  id: number;
  sku: string;
  name: string;
  modelo?: string | null;
  imei?: string | null;
  serial?: string | null;
};

export type SaleStoreSummary = {
  id: number;
  name: string;
  location?: string | null;
};

export type SaleUserSummary = {
  id: number;
  username: string;
  full_name?: string | null;
};

export type SaleItem = {
  id: number;
  sale_id: number;
  device_id: number;
  quantity: number;
  unit_price: number;
  discount_amount: number;
  total_line: number;
  device?: SaleDeviceSummary | null;
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
  store?: SaleStoreSummary | null;
  performed_by?: SaleUserSummary | null;
};

export type SalesFilters = {
  storeId?: number | null;
  customerId?: number | null;
  userId?: number | null;
  dateFrom?: string;
  dateTo?: string;
  query?: string;
  limit?: number;
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

export type PurchaseImportResponse = {
  imported: number;
  orders: PurchaseOrder[];
  errors: string[];
};

export type RecurringOrderType = "purchase" | "transfer";

export type RecurringOrder = {
  id: number;
  name: string;
  description?: string | null;
  order_type: RecurringOrderType;
  store_id?: number | null;
  store_name?: string | null;
  payload: Record<string, unknown>;
  created_by_id?: number | null;
  created_by_name?: string | null;
  last_used_by_id?: number | null;
  last_used_by_name?: string | null;
  created_at: string;
  updated_at: string;
  last_used_at?: string | null;
};

export type RecurringOrderPayload = {
  name: string;
  description?: string | null;
  order_type: RecurringOrderType;
  payload: Record<string, unknown>;
};

export type RecurringOrderExecutionResult = {
  template_id: number;
  order_type: RecurringOrderType;
  reference_id: number;
  store_id?: number | null;
  created_at: string;
  summary: string;
};

export type OperationsHistoryRecord = {
  id: string;
  operation_type: "purchase" | "transfer_dispatch" | "transfer_receive" | "sale";
  occurred_at: string;
  store_id?: number | null;
  store_name?: string | null;
  technician_id?: number | null;
  technician_name?: string | null;
  reference?: string | null;
  description: string;
  amount?: number | null;
};

export type OperationsTechnicianSummary = {
  id: number;
  name: string;
};

export type OperationsHistoryResponse = {
  records: OperationsHistoryRecord[];
  technicians: OperationsTechnicianSummary[];
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
  categoria?: string;
  condicion?: string;
  estado?: string;
  ubicacion?: string;
  proveedor?: string;
  fecha_ingreso_desde?: string;
  fecha_ingreso_hasta?: string;
};

export type DeviceImportSummary = {
  created: number;
  updated: number;
  skipped: number;
  errors: Array<{ row: number; message: string }>;
};

export type SmartImportColumnMatch = {
  campo: string;
  encabezado_origen: string | null;
  estado: "ok" | "pendiente" | "falta";
  tipo_dato?: string | null;
  ejemplos: string[];
};

export type InventorySmartImportPreview = {
  columnas: SmartImportColumnMatch[];
  columnas_detectadas: Record<string, string | null>;
  columnas_faltantes: string[];
  total_filas: number;
  registros_incompletos_estimados: number;
  advertencias: string[];
  patrones_sugeridos: Record<string, string>;
};

export type InventorySmartImportResult = {
  total_procesados: number;
  nuevos: number;
  actualizados: number;
  registros_incompletos: number;
  columnas_faltantes: string[];
  advertencias: string[];
  tiendas_nuevas: string[];
  duracion_segundos?: number | null;
  resumen: string;
};

export type InventorySmartImportResponse = {
  preview: InventorySmartImportPreview;
  resultado?: InventorySmartImportResult | null;
};

export type InventoryImportHistoryEntry = {
  id: number;
  nombre_archivo: string;
  fecha: string;
  columnas_detectadas: Record<string, string | null>;
  registros_incompletos: number;
  total_registros: number;
  nuevos: number;
  actualizados: number;
  advertencias: string[];
  duracion_segundos?: number | null;
};

export type MovementInput = {
  producto_id: number;
  tipo_movimiento: "entrada" | "salida" | "ajuste";
  cantidad: number;
  comentario: string;
  sucursal_origen_id?: number | null;
  sucursal_destino_id?: number | null;
  unit_cost?: number;
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

export type TransferReportDevice = {
  sku?: string | null;
  name?: string | null;
  quantity: number;
};

export type TransferReportItem = {
  id: number;
  folio: string;
  origin_store: string;
  destination_store: string;
  status: TransferOrder["status"];
  reason?: string | null;
  requested_at: string;
  dispatched_at?: string | null;
  received_at?: string | null;
  cancelled_at?: string | null;
  requested_by?: string | null;
  dispatched_by?: string | null;
  received_by?: string | null;
  cancelled_by?: string | null;
  total_quantity: number;
  devices: TransferReportDevice[];
};

export type TransferReportTotals = {
  total_transfers: number;
  pending: number;
  in_transit: number;
  completed: number;
  cancelled: number;
  total_quantity: number;
};

export type TransferReportFilters = {
  store_id?: number;
  origin_store_id?: number;
  destination_store_id?: number;
  status?: TransferOrder["status"];
  date_from?: string;
  date_to?: string;
};

export type TransferReport = {
  generated_at: string;
  filters: TransferReportFilters;
  totals: TransferReportTotals;
  items: TransferReportItem[];
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

export type InventoryCurrentStoreReport = {
  store_id: number;
  store_name: string;
  device_count: number;
  total_units: number;
  total_value: number;
};

export type InventoryTotals = {
  stores: number;
  devices: number;
  total_units: number;
  total_value: number;
};

export type InventoryCurrentReport = {
  stores: InventoryCurrentStoreReport[];
  totals: InventoryTotals;
};

export type MovementTypeSummary = {
  tipo_movimiento: MovementInput["tipo_movimiento"];
  total_cantidad: number;
  total_valor: number;
};

export type MovementPeriodSummary = {
  periodo: string;
  tipo_movimiento: MovementInput["tipo_movimiento"];
  total_cantidad: number;
  total_valor: number;
};

export type MovementReportEntry = {
  id: number;
  tipo_movimiento: MovementInput["tipo_movimiento"];
  cantidad: number;
  valor_total: number;
  sucursal_destino_id?: number | null;
  sucursal_destino?: string | null;
  sucursal_origen_id?: number | null;
  sucursal_origen?: string | null;
  comentario?: string | null;
  usuario?: string | null;
  fecha: string;
};

export type InventoryMovementsSummary = {
  total_movimientos: number;
  total_unidades: number;
  total_valor: number;
  por_tipo: MovementTypeSummary[];
};

export type InventoryMovementsReport = {
  resumen: InventoryMovementsSummary;
  periodos: MovementPeriodSummary[];
  movimientos: MovementReportEntry[];
};

export type TopProductReportItem = {
  device_id: number;
  sku: string;
  nombre: string;
  store_id: number;
  store_name: string;
  unidades_vendidas: number;
  ingresos_totales: number;
  margen_estimado: number;
};

export type TopProductsReport = {
  items: TopProductReportItem[];
  total_unidades: number;
  total_ingresos: number;
};

export type InventoryValueStore = {
  store_id: number;
  store_name: string;
  valor_total: number;
  valor_costo: number;
  margen_total: number;
};

export type InventoryValueTotals = {
  valor_total: number;
  valor_costo: number;
  margen_total: number;
};

export type InventoryValueReport = {
  stores: InventoryValueStore[];
  totals: InventoryValueTotals;
};

export type InventoryCurrentFilters = {
  storeIds?: number[];
};

export type InventoryValueFilters = InventoryCurrentFilters & {
  categories?: string[];
};

export type InventoryMovementsFilters = InventoryCurrentFilters & {
  dateFrom?: string;
  dateTo?: string;
  movementType?: MovementInput["tipo_movimiento"];
};

export type InventoryTopProductsFilters = InventoryCurrentFilters & {
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
};

export type DashboardPoint = {
  label: string;
  value: number;
};

export type AuditHighlight = {
  id: number;
  action: string;
  created_at: string;
  severity: "info" | "warning" | "critical";
  entity_type: string;
  entity_id: string;
  status: "pending" | "acknowledged";
  acknowledged_at?: string | null;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  acknowledged_note?: string | null;
};

export type AuditAcknowledgedEntity = {
  entity_type: string;
  entity_id: string;
  acknowledged_at: string;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  note?: string | null;
};

export type DashboardAuditAlerts = {
  total: number;
  critical: number;
  warning: number;
  info: number;
  has_alerts: boolean;
  pending_count: number;
  acknowledged_count: number;
  highlights: AuditHighlight[];
  acknowledged_entities: AuditAcknowledgedEntity[];
};

export type GlobalReportFiltersState = {
  date_from?: string | null;
  date_to?: string | null;
  module?: string | null;
  severity?: SystemLogLevel | null;
};

export type GlobalReportTotals = {
  logs: number;
  errors: number;
  info: number;
  warning: number;
  error: number;
  critical: number;
  sync_pending: number;
  sync_failed: number;
  last_activity_at?: string | null;
};

export type GlobalReportBreakdownItem = {
  name: string;
  total: number;
};

export type GlobalReportAlert = {
  type: "critical_log" | "system_error" | "sync_failure";
  level: SystemLogLevel;
  message: string;
  module?: string | null;
  occurred_at?: string | null;
  reference?: string | null;
  count: number;
};

export type GlobalReportLogEntry = {
  id_log: number;
  usuario?: string | null;
  modulo: string;
  accion: string;
  descripcion: string;
  fecha: string;
  nivel: SystemLogLevel;
  ip_origen?: string | null;
};

export type GlobalReportErrorEntry = {
  id_error: number;
  mensaje: string;
  stack_trace?: string | null;
  modulo: string;
  fecha: string;
  usuario?: string | null;
};

export type GlobalReportOverview = {
  generated_at: string;
  filters: GlobalReportFiltersState;
  totals: GlobalReportTotals;
  module_breakdown: GlobalReportBreakdownItem[];
  severity_breakdown: GlobalReportBreakdownItem[];
  recent_logs: GlobalReportLogEntry[];
  recent_errors: GlobalReportErrorEntry[];
  alerts: GlobalReportAlert[];
};

export type GlobalReportSeriesPoint = {
  date: string;
  info: number;
  warning: number;
  error: number;
  critical: number;
  system_errors: number;
};

export type GlobalReportDashboard = {
  generated_at: string;
  filters: GlobalReportFiltersState;
  activity_series: GlobalReportSeriesPoint[];
  module_distribution: GlobalReportBreakdownItem[];
  severity_distribution: GlobalReportBreakdownItem[];
};

export type AuditReminderEntry = {
  entity_type: string;
  entity_id: string;
  first_seen: string;
  last_seen: string;
  occurrences: number;
  latest_action: string;
  latest_details?: string | null;
  status: "pending" | "acknowledged";
  acknowledged_at?: string | null;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  acknowledged_note?: string | null;
};

export type AuditReminderSummary = {
  threshold_minutes: number;
  min_occurrences: number;
  total: number;
  pending_count: number;
  acknowledged_count: number;
  persistent: AuditReminderEntry[];
};

export type AuditAcknowledgementInput = {
  entity_type: string;
  entity_id: string;
  note?: string;
};

export type AuditAcknowledgementResponse = {
  entity_type: string;
  entity_id: string;
  acknowledged_at: string;
  acknowledged_by_id?: number | null;
  acknowledged_by_name?: string | null;
  note?: string | null;
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
  audit_alerts: DashboardAuditAlerts;
};

export type AuditLogEntry = {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: string | null;
  performed_by_id?: number | null;
  created_at: string;
  severity: "info" | "warning" | "critical";
  severity_label: string;
};

export type AuditLogFilters = {
  limit?: number;
  action?: string;
  entity_type?: string;
  performed_by_id?: number;
  date_from?: string;
  date_to?: string;
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
  store_id: number;
  store_name: string;
  average_daily_sales: number;
  projected_days: number | null;
  quantity: number;
  trend: string;
  trend_score: number;
  confidence: number;
  alert_level: string | null;
  sold_units: number;
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
  trend: string;
  trend_score: number;
  revenue_trend_score: number;
  r2_revenue: number;
};

export type AnalyticsSalesProjection = {
  items: SalesProjectionMetric[];
};

export type AnalyticsAlert = {
  type: string;
  level: string;
  message: string;
  store_id: number | null;
  store_name: string;
  device_id: number | null;
  sku: string | null;
};

export type AnalyticsAlerts = {
  items: AnalyticsAlert[];
};

export type StoreRealtimeWidget = {
  store_id: number;
  store_name: string;
  inventory_value: number;
  sales_today: number;
  last_sale_at: string | null;
  low_stock_devices: number;
  pending_repairs: number;
  last_sync_at: string | null;
  trend: string;
  trend_score: number;
  confidence: number;
};

export type AnalyticsRealtime = {
  items: StoreRealtimeWidget[];
};

export type AnalyticsCategories = {
  categories: string[];
};

export type AnalyticsFilters = {
  storeIds?: number[];
  dateFrom?: string;
  dateTo?: string;
  category?: string;
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

// [PACK35-frontend]
export type SyncQueueStatus = "PENDING" | "SENT" | "FAILED";

export type SyncQueueEntry = {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
  idempotency_key: string | null;
  status: SyncQueueStatus;
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type SyncQueueSummary = {
  percent: number;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  last_updated: string | null;
  oldest_pending: string | null;
}; // [PACK35-frontend]

// [PACK35-frontend]
export type SyncHybridComponent = {
  total: number;
  processed: number;
  pending: number;
  failed: number;
  latest_update: string | null;
  oldest_pending: string | null;
};

// [PACK35-frontend]
export type SyncHybridProgress = {
  percent: number;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  components: {
    queue: SyncHybridComponent;
    outbox: SyncHybridComponent;
  };
};

// [PACK35-frontend]
export type SyncHybridForecast = {
  lookback_minutes: number;
  processed_recent: number;
  processed_queue: number;
  processed_outbox: number;
  attempts_total: number;
  attempts_successful: number;
  success_rate: number;
  events_per_minute: number;
  backlog_pending: number;
  backlog_failed: number;
  backlog_total: number;
  estimated_minutes_remaining: number | null;
  estimated_completion: string | null;
  generated_at: string;
  progress: SyncHybridProgress;
};

// [PACK35-frontend]
export type SyncHybridModuleBreakdownComponent = {
  total: number;
  processed: number;
  pending: number;
  failed: number;
};

// [PACK35-frontend]
export type SyncHybridModuleBreakdownItem = {
  module: string;
  label: string;
  total: number;
  processed: number;
  pending: number;
  failed: number;
  percent: number;
  queue: SyncHybridModuleBreakdownComponent;
  outbox: SyncHybridModuleBreakdownComponent;
};

export type SyncQueueEnqueueResponse = {
  queued: SyncQueueEntry[];
  reused: SyncQueueEntry[];
};

export type SyncQueueDispatchResult = {
  processed: number;
  sent: number;
  failed: number;
  retried: number;
};

export type SyncQueueEventInput = {
  event_type: string;
  payload: Record<string, unknown>;
  idempotency_key?: string | null;
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

export type SyncBranchHealth = "operativa" | "alerta" | "critica" | "sin_registros";

export type SyncBranchOverview = {
  store_id: number;
  store_name: string;
  store_code: string;
  timezone: string;
  inventory_value: number;
  last_sync_at?: string | null;
  last_sync_mode?: string | null;
  last_sync_status?: string | null;
  health: SyncBranchHealth;
  health_label: string;
  pending_transfers: number;
  open_conflicts: number;
};

export type SyncConflictStoreDetail = {
  store_id: number;
  store_name: string;
  quantity: number;
};

export type SyncConflictLog = {
  id: number;
  sku: string;
  product_name?: string | null;
  detected_at: string;
  difference: number;
  severity: SyncBranchHealth;
  stores_max: SyncConflictStoreDetail[];
  stores_min: SyncConflictStoreDetail[];
};

export type SyncConflictFilters = {
  store_id?: number;
  date_from?: string;
  date_to?: string;
  severity?: SyncBranchHealth;
  limit?: number;
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

const API_URL = (import.meta.env.VITE_API_URL?.trim() ?? "") || getApiBaseUrl();

const REQUEST_CACHE_TTL_MS = 60_000;
const REQUEST_CACHE_MAX_ENTRIES = 128;

type RequestCacheRecord = {
  timestamp: number;
  value: unknown;
};

const requestCache = new Map<string, RequestCacheRecord>();
type PendingRequestResult = { value: unknown; isJson: boolean };
const pendingRequests = new Map<string, Promise<PendingRequestResult>>();

function serializeHeaders(headers: Headers): Array<[string, string]> {
  return Array.from(headers.entries())
    .filter(([key]) => key.toLowerCase() !== "authorization")
    .map(([key, value]) => [key.toLowerCase(), value])
    .sort((a, b) => {
      if (a[0] === b[0]) {
        return a[1].localeCompare(b[1]);
      }
      return a[0].localeCompare(b[0]);
    });
}

function buildCacheKey(path: string, headers: Headers, token?: string): string {
  const tokenKey = token ? token.slice(-16) : "";
  return `${tokenKey}|${path}|${JSON.stringify(serializeHeaders(headers))}`;
}

function cloneData<T>(value: T): T {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value)) as T;
}

function setCacheEntry(key: string, value: unknown) {
  if (requestCache.size >= REQUEST_CACHE_MAX_ENTRIES) {
    const oldestEntry = requestCache.keys().next();
    if (!oldestEntry.done) {
      requestCache.delete(oldestEntry.value);
    }
  }
  requestCache.set(key, { timestamp: Date.now(), value });
}

export function clearRequestCache(): void {
  requestCache.clear();
  pendingRequests.clear();
}

function buildStoreQuery(storeIds?: number[]): string {
  if (!storeIds || storeIds.length === 0) {
    return "";
  }
  const params = storeIds.map((id) => `store_ids=${encodeURIComponent(id)}`).join("&");
  return `?${params}`;
}

function buildAnalyticsQuery(filters?: AnalyticsFilters): string {
  if (!filters) {
    return "";
  }
  const params = new URLSearchParams();
  if (filters.storeIds && filters.storeIds.length > 0) {
    filters.storeIds.forEach((id) => {
      params.append("store_ids", String(id));
    });
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.category) {
    params.set("category", filters.category);
  }
  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

export const NETWORK_EVENT = "softmobile:network-error";
export const NETWORK_RECOVERY_EVENT = "softmobile:network-recovered";
export const UNAUTHORIZED_EVENT = "softmobile:unauthorized";

function emitNetworkEvent(type: typeof NETWORK_EVENT | typeof NETWORK_RECOVERY_EVENT, message?: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(type, {
      detail: message,
    }),
  );
}

function emitUnauthorizedEvent(message?: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent(UNAUTHORIZED_EVENT, {
      detail: message,
    }),
  );
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!headers.has("Content-Type") && !isFormData) {
    headers.set("Content-Type", "application/json");
  }
  if (isFormData) {
    headers.delete("Content-Type");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const method = (options.method ?? "GET").toUpperCase();
  const shouldUseCache = method === "GET" && options.cache !== "no-store";
  const cacheKey = shouldUseCache ? buildCacheKey(path, headers, token) : null;

  if (cacheKey) {
    const cached = requestCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp <= REQUEST_CACHE_TTL_MS) {
      return cloneData(cached.value as T);
    }

    const pending = pendingRequests.get(cacheKey);
    if (pending) {
      const { value, isJson } = await pending;
      return isJson ? cloneData(value as T) : (value as T);
    }
  }

  const executeNetworkRequest = async (): Promise<PendingRequestResult> => {
    let response: Response;
    try {
      response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
      });
    } catch (error) {
      emitNetworkEvent(
        NETWORK_EVENT,
        "No fue posible contactar la API de Softmobile. Verifica tu conexión o intenta nuevamente en unos segundos.",
      );
      if (error instanceof Error && error.name === "AbortError") {
        throw error;
      }
      throw new Error("Error de red: la API no respondió");
    }

    if (!response.ok) {
      if (response.status >= 500 || response.status === 0) {
        emitNetworkEvent(
          NETWORK_EVENT,
          `La API respondió con un estado ${response.status}. Reintenta una vez restablecida la conexión corporativa.`,
        );
      }
      let detailText: string | null = null;
      let parsedDetail: unknown = null;
      try {
        detailText = await response.text();
        parsedDetail = detailText ? JSON.parse(detailText) : null;
      } catch (parseError) {
        if (!(parseError instanceof SyntaxError)) {
          throw parseError;
        }
      }

      const detailMessage =
        parsedDetail && typeof parsedDetail === "object" && "detail" in parsedDetail
          ? String((parsedDetail as { detail: unknown }).detail)
          : detailText || `Error ${response.status}`;

      if (response.status === 401) {
        emitUnauthorizedEvent(detailMessage);
        clearRequestCache();
      }

      throw new Error(detailMessage);
    }

    emitNetworkEvent(NETWORK_RECOVERY_EVENT);

    if (response.status === 204) {
      if (method !== "GET") {
        clearRequestCache();
      }
      return { value: undefined, isJson: false };
    }

    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");
    let parsed: T;

    if (isJson) {
      parsed = (await response.json()) as T;
    } else {
      parsed = (await response.blob()) as unknown as T;
    }

    if (cacheKey && isJson) {
      setCacheEntry(cacheKey, cloneData(parsed));
    }

    if (method !== "GET") {
      clearRequestCache();
    }

    return { value: parsed, isJson };
  };

  const networkPromise = executeNetworkRequest();

  if (cacheKey) {
    pendingRequests.set(cacheKey, networkPromise);
  }

  try {
    const { value, isJson } = await networkPromise;
    return isJson ? cloneData(value as T) : (value as T);
  } finally {
    if (cacheKey) {
      pendingRequests.delete(cacheKey);
    }
  }
}

function extractCollectionItems<T>(payload: PaginatedResponse<T> | T[]): T[] {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.items)) {
    return payload.items;
  }
  return [];
}

function requestCollection<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T[]> {
  return request<PaginatedResponse<T> | T[]>(path, options, token).then((payload) =>
    extractCollectionItems(payload),
  );
}

export function getBootstrapStatus(): Promise<BootstrapStatus> {
  return request<BootstrapStatus>("/auth/bootstrap/status", { method: "GET" });
}

export function bootstrapAdmin(payload: BootstrapRequest): Promise<UserAccount> {
  const bodyPayload: Record<string, unknown> = {
    username: payload.username,
    password: payload.password,
    roles: [],
  };

  if (payload.full_name) {
    bodyPayload.full_name = payload.full_name;
  }

  if (payload.telefono) {
    bodyPayload.telefono = payload.telefono;
  }

  return request<UserAccount>("/auth/bootstrap", {
    method: "POST",
    body: JSON.stringify(bodyPayload),
  });
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

export function listUsers(
  token: string,
  filters: UserQueryFilters = {},
  options: { signal?: AbortSignal } = {},
): Promise<UserAccount[]> {
  const params = new URLSearchParams();
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.role) {
    params.set("role", filters.role);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (typeof filters.storeId === "number") {
    params.set("store_id", String(filters.storeId));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<UserAccount>(
    `/users${suffix}`,
    { method: "GET", signal: options.signal },
    token,
  );
}

export function listRoles(token: string): Promise<Role[]> {
  return requestCollection<Role>("/users/roles", { method: "GET" }, token);
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

export function createUser(
  token: string,
  payload: UserCreateInput,
  reason?: string,
): Promise<UserAccount> {
  const headers: Record<string, string> = {};
  if (reason) {
    headers["X-Reason"] = reason;
  }
  return request<UserAccount>("/users", { method: "POST", body: JSON.stringify(payload), headers }, token);
}

export function updateUser(
  token: string,
  userId: number,
  payload: UserUpdateInput,
  reason: string,
): Promise<UserAccount> {
  return request<UserAccount>(
    `/users/${userId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function listRolePermissions(token: string, role?: string): Promise<RolePermissionMatrix[]> {
  const params = new URLSearchParams();
  if (role) {
    params.set("role", role);
  }
  const suffix = params.toString() ? `?${params}` : "";
  return requestCollection<RolePermissionMatrix>(
    `/users/permissions${suffix}`,
    { method: "GET" },
    token,
  );
}

export function updateRolePermissions(
  token: string,
  role: string,
  permissions: RoleModulePermission[],
  reason: string,
): Promise<RolePermissionMatrix> {
  return request<RolePermissionMatrix>(
    `/users/roles/${encodeURIComponent(role)}/permissions`,
    {
      method: "PUT",
      body: JSON.stringify({ permissions }),
      headers: { "X-Reason": reason },
    },
    token,
  );
}

export function getUserDashboard(token: string): Promise<UserDashboardMetrics> {
  return request<UserDashboardMetrics>("/users/dashboard", { method: "GET" }, token);
}

export function exportUsers(
  token: string,
  format: "pdf" | "xlsx",
  filters: UserQueryFilters = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  params.set("format", format);
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.role) {
    params.set("role", filters.role);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (typeof filters.storeId === "number") {
    params.set("store_id", String(filters.storeId));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<Blob>(
    `/users/export${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function getStores(token: string): Promise<Store[]> {
  return requestCollection<Store>("/stores/?limit=200", { method: "GET" }, token);
}

export function getSummary(token: string): Promise<Summary[]> {
  return requestCollection<Summary>("/inventory/summary", { method: "GET" }, token);
}

export function getInventoryCurrentReport(
  token: string,
  filters: InventoryCurrentFilters = {},
): Promise<InventoryCurrentReport> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryCurrentReport>(`/reports/inventory/current${suffix}`, { method: "GET" }, token);
}

export function getInventoryValueReport(
  token: string,
  filters: InventoryValueFilters = {},
): Promise<InventoryValueReport> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryValueReport>(`/reports/inventory/value${suffix}`, { method: "GET" }, token);
}

export function getInventoryMovementsReport(
  token: string,
  filters: InventoryMovementsFilters = {},
): Promise<InventoryMovementsReport> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<InventoryMovementsReport>(
    `/reports/inventory/movements${suffix}`,
    { method: "GET" },
    token,
  );
}

export function getTopProductsReport(
  token: string,
  filters: InventoryTopProductsFilters = {},
): Promise<TopProductsReport> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<TopProductsReport>(`/reports/inventory/top-products${suffix}`, { method: "GET" }, token);
}

export type DeviceListFilters = {
  search?: string;
  estado?: Device["estado_comercial"];
  categoria?: string;
  condicion?: string;
  estado_inventario?: string;
  ubicacion?: string;
  proveedor?: string;
  fecha_ingreso_desde?: string;
  fecha_ingreso_hasta?: string;
};

function buildDeviceFilterParams(filters: DeviceListFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search) {
    params.append("search", filters.search);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.categoria) {
    params.append("categoria", filters.categoria);
  }
  if (filters.condicion) {
    params.append("condicion", filters.condicion);
  }
  if (filters.estado_inventario) {
    params.append("estado_inventario", filters.estado_inventario);
  }
  if (filters.ubicacion) {
    params.append("ubicacion", filters.ubicacion);
  }
  if (filters.proveedor) {
    params.append("proveedor", filters.proveedor);
  }
  if (filters.fecha_ingreso_desde) {
    params.append("fecha_ingreso_desde", filters.fecha_ingreso_desde);
  }
  if (filters.fecha_ingreso_hasta) {
    params.append("fecha_ingreso_hasta", filters.fecha_ingreso_hasta);
  }
  return params;
}

function appendNumericList(params: URLSearchParams, key: string, values?: number[]): void {
  if (!values) {
    return;
  }
  for (const value of values) {
    params.append(key, String(value));
  }
}

function appendStringList(params: URLSearchParams, key: string, values?: string[]): void {
  if (!values) {
    return;
  }
  for (const value of values) {
    if (value) {
      params.append(key, value);
    }
  }
}

function buildSalesFilterParams(filters: SalesFilters = {}): URLSearchParams {
  const params = new URLSearchParams();
  if (typeof filters.storeId === "number") {
    params.append("store_id", String(filters.storeId));
  }
  if (typeof filters.customerId === "number") {
    params.append("customer_id", String(filters.customerId));
  }
  if (typeof filters.userId === "number") {
    params.append("performed_by_id", String(filters.userId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  return params;
}

function buildInventoryValueParams(filters: InventoryValueFilters = {}): URLSearchParams {
  const params = new URLSearchParams();
  appendNumericList(params, "store_ids", filters.storeIds);
  appendStringList(params, "categories", filters.categories);
  return params;
}

function buildInventoryMovementsParams(filters: InventoryMovementsFilters = {}): URLSearchParams {
  const params = buildInventoryValueParams(filters);
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.movementType) {
    params.append("movement_type", filters.movementType);
  }
  return params;
}

function buildTopProductsParams(filters: InventoryTopProductsFilters = {}): URLSearchParams {
  const params = buildInventoryValueParams(filters);
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  return params;
}

export function getDevices(
  token: string,
  storeId: number,
  filters: DeviceListFilters = {}
): Promise<Device[]> {
  const params = buildDeviceFilterParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<Device>(`/stores/${storeId}/devices${suffix}`, { method: "GET" }, token);
}

export function getDeviceIdentifier(
  token: string,
  storeId: number,
  deviceId: number,
): Promise<DeviceIdentifier> {
  return request<DeviceIdentifier>(
    `/inventory/stores/${storeId}/devices/${deviceId}/identifier`,
    { method: "GET" },
    token,
  );
}

export function upsertDeviceIdentifier(
  token: string,
  storeId: number,
  deviceId: number,
  payload: DeviceIdentifierInput,
  reason: string,
): Promise<DeviceIdentifier> {
  return request<DeviceIdentifier>(
    `/inventory/stores/${storeId}/devices/${deviceId}/identifier`,
    {
      method: "PUT",
      headers: { "X-Reason": reason },
      body: JSON.stringify(payload),
    },
    token,
  );
}

export async function exportStoreDevicesCsv(
  token: string,
  storeId: number,
  filters: DeviceListFilters = {},
  reason: string,
): Promise<void> {
  const params = buildDeviceFilterParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/inventory/stores/${storeId}/devices/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar el catálogo de productos");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `softmobile_catalogo_${storeId}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function importStoreDevicesCsv(
  token: string,
  storeId: number,
  file: File,
  reason: string,
): Promise<DeviceImportSummary> {
  const formData = new FormData();
  formData.append("file", file);
  return request<DeviceImportSummary>(
    `/inventory/stores/${storeId}/devices/import`,
    { method: "POST", body: formData, headers: { "X-Reason": reason } },
    token,
  );
}

export function smartInventoryImport(
  token: string,
  file: File,
  reason: string,
  options: { commit?: boolean; overrides?: Record<string, string> } = {},
): Promise<InventorySmartImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("commit", options.commit ? "true" : "false");
  if (options.overrides && Object.keys(options.overrides).length > 0) {
    formData.append("overrides", JSON.stringify(options.overrides));
  }
  return request<InventorySmartImportResponse>(
    "/inventory/import/smart",
    { method: "POST", body: formData, headers: { "X-Reason": reason } },
    token,
  );
}

export function getSmartImportHistory(
  token: string,
  limit = 10,
): Promise<InventoryImportHistoryEntry[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return requestCollection<InventoryImportHistoryEntry>(
    `/inventory/import/smart/history?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function getIncompleteDevices(
  token: string,
  storeId?: number,
  limit = 100,
): Promise<Device[]> {
  const params = new URLSearchParams();
  if (storeId != null) {
    params.set("store_id", String(storeId));
  }
  params.set("limit", String(limit));
  const query = params.toString();
  const url = query ? `/inventory/devices/incomplete?${query}` : "/inventory/devices/incomplete";
  return requestCollection<Device>(url, { method: "GET" }, token);
}

export function updateDevice(
  token: string,
  storeId: number,
  deviceId: number,
  payload: DeviceUpdateInput,
  reason: string
): Promise<Device> {
  return request<Device>(
    `/inventory/stores/${storeId}/devices/${deviceId}`,
    { method: "PATCH", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function getImportValidationReport(token: string): Promise<ImportValidationSummary> {
  return request<ImportValidationSummary>("/validacion/reporte", { method: "GET" }, token);
}

export function getPendingImportValidations(
  token: string,
  limit = 200,
): Promise<ImportValidationDetail[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestCollection<ImportValidationDetail>(
    `/validacion/pendientes?${params.toString()}`,
    { method: "GET" },
    token,
  );
}

export function markImportValidationCorrected(
  token: string,
  validationId: number,
  reason: string,
): Promise<ImportValidation> {
  return request<ImportValidation>(
    `/validacion/${validationId}/corregir`,
    { method: "PATCH", headers: { "X-Reason": reason } },
    token,
  );
}

export function listPurchaseOrders(token: string, storeId: number, limit = 50): Promise<PurchaseOrder[]> {
  const params = new URLSearchParams({ limit: String(limit), store_id: String(storeId) });
  return requestCollection<PurchaseOrder>(
    `/purchases/?${params.toString()}`,
    { method: "GET" },
    token,
  );
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

export function importPurchaseOrdersCsv(
  token: string,
  file: File,
  reason: string
): Promise<PurchaseImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<PurchaseImportResponse>(
    "/purchases/import",
    {
      method: "POST",
      body: formData,
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function listPurchaseVendors(
  token: string,
  filters: { query?: string; status?: string; limit?: number } = {}
): Promise<PurchaseVendor[]> {
  const params = new URLSearchParams();
  if (filters.query) {
    params.append("q", filters.query);
  }
  if (filters.status) {
    params.append("estado", filters.status);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<PurchaseVendor>(
    `/purchases/vendors${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createPurchaseVendor(
  token: string,
  payload: PurchaseVendorPayload,
  reason: string
): Promise<PurchaseVendor> {
  return request<PurchaseVendor>(
    "/purchases/vendors",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function updatePurchaseVendor(
  token: string,
  vendorId: number,
  payload: PurchaseVendorPayload,
  reason: string
): Promise<PurchaseVendor> {
  return request<PurchaseVendor>(
    `/purchases/vendors/${vendorId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function setPurchaseVendorStatus(
  token: string,
  vendorId: number,
  payload: PurchaseVendorStatusPayload,
  reason: string
): Promise<PurchaseVendor> {
  return request<PurchaseVendor>(
    `/purchases/vendors/${vendorId}/status`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export async function exportPurchaseVendorsCsv(
  token: string,
  filters: { query?: string; status?: string } = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters.query) {
    params.append("q", filters.query);
  }
  if (filters.status) {
    params.append("estado", filters.status);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/purchases/vendors/export/csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function getPurchaseVendorHistory(
  token: string,
  vendorId: number,
  filters: { limit?: number; dateFrom?: string; dateTo?: string } = {}
): Promise<PurchaseVendorHistory> {
  const params = new URLSearchParams();
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<PurchaseVendorHistory>(
    `/purchases/vendors/${vendorId}/history${suffix}`,
    { method: "GET" },
    token,
  );
}

export function listPurchaseRecords(
  token: string,
  filters: {
    proveedorId?: number;
    usuarioId?: number;
    dateFrom?: string;
    dateTo?: string;
    estado?: string;
    query?: string;
    limit?: number;
    offset?: number;
  } = {}
): Promise<PurchaseRecord[]> {
  const params = new URLSearchParams();
  if (filters.proveedorId) {
    params.append("proveedor_id", String(filters.proveedorId));
  }
  if (filters.usuarioId) {
    params.append("usuario_id", String(filters.usuarioId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  if (typeof filters.limit === "number") {
    params.append("limit", String(filters.limit));
  }
  if (typeof filters.offset === "number") {
    params.append("offset", String(filters.offset));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<PurchaseRecord>(
    `/purchases/records${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createPurchaseRecord(
  token: string,
  payload: PurchaseRecordPayload,
  reason: string
): Promise<PurchaseRecord> {
  return request<PurchaseRecord>(
    "/purchases/records",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token,
  );
}

export function exportPurchaseRecordsPdf(
  token: string,
  filters: {
    proveedorId?: number;
    usuarioId?: number;
    dateFrom?: string;
    dateTo?: string;
    estado?: string;
    query?: string;
  } = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters.proveedorId) {
    params.append("proveedor_id", String(filters.proveedorId));
  }
  if (filters.usuarioId) {
    params.append("usuario_id", String(filters.usuarioId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/purchases/records/export/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function exportPurchaseRecordsExcel(
  token: string,
  filters: {
    proveedorId?: number;
    usuarioId?: number;
    dateFrom?: string;
    dateTo?: string;
    estado?: string;
    query?: string;
  } = {},
  reason: string,
): Promise<Blob> {
  const params = new URLSearchParams();
  if (filters.proveedorId) {
    params.append("proveedor_id", String(filters.proveedorId));
  }
  if (filters.usuarioId) {
    params.append("usuario_id", String(filters.usuarioId));
  }
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (filters.estado) {
    params.append("estado", filters.estado);
  }
  if (filters.query) {
    params.append("q", filters.query);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/purchases/records/export/xlsx${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function getPurchaseStatistics(
  token: string,
  filters: { dateFrom?: string; dateTo?: string; topLimit?: number } = {}
): Promise<PurchaseStatistics> {
  const params = new URLSearchParams();
  if (filters.dateFrom) {
    params.append("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.append("date_to", filters.dateTo);
  }
  if (typeof filters.topLimit === "number") {
    params.append("top_limit", String(filters.topLimit));
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<PurchaseStatistics>(`/purchases/statistics${suffix}`, { method: "GET" }, token);
}

type CustomerListOptions = {
  query?: string;
  limit?: number;
  status?: string;
  customerType?: string;
  hasDebt?: boolean;
  statusFilter?: string;
  customerTypeFilter?: string;
};

export function listCustomers(
  token: string,
  options: CustomerListOptions = {}
): Promise<Customer[]> {
  const params = new URLSearchParams();
  params.append("limit", String(options.limit ?? 100));
  if (options.query) {
    params.append("q", options.query);
  }
  if (options.status) {
    params.append("status", options.status);
  }
  if (options.customerType) {
    params.append("customer_type", options.customerType);
  }
  if (typeof options.hasDebt === "boolean") {
    params.append("has_debt", String(options.hasDebt));
  }
  if (options.statusFilter) {
    params.append("status_filter", options.statusFilter);
  }
  if (options.customerTypeFilter) {
    params.append("customer_type_filter", options.customerTypeFilter);
  }
  const queryString = params.toString();
  return requestCollection<Customer>(`/customers?${queryString}`, { method: "GET" }, token);
}

export function exportCustomersCsv(
  token: string,
  options: CustomerListOptions = {}
): Promise<Blob> {
  const params = new URLSearchParams({ export: "csv" });
  if (options.query) {
    params.append("q", options.query);
  }
  if (options.status) {
    params.append("status", options.status);
  }
  if (options.customerType) {
    params.append("customer_type", options.customerType);
  }
  if (typeof options.hasDebt === "boolean") {
    params.append("has_debt", String(options.hasDebt));
  }
  if (options.statusFilter) {
    params.append("status_filter", options.statusFilter);
  }
  if (options.customerTypeFilter) {
    params.append("customer_type_filter", options.customerTypeFilter);
  }
  const queryString = params.toString();
  return request<Blob>(`/customers?${queryString}`, { method: "GET" }, token);
}

export function getCustomerPortfolio(
  token: string,
  params: {
    category?: "delinquent" | "frequent";
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  } = {}
): Promise<CustomerPortfolioReport> {
  const searchParams = new URLSearchParams();
  searchParams.append("category", params.category ?? "delinquent");
  if (typeof params.limit === "number") {
    searchParams.append("limit", String(params.limit));
  }
  if (params.dateFrom) {
    searchParams.append("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.append("date_to", params.dateTo);
  }
  const queryString = searchParams.toString();
  return request<CustomerPortfolioReport>(
    `/reports/customers/portfolio?${queryString}`,
    { method: "GET" },
    token
  );
}

export function exportCustomerPortfolioPdf(
  token: string,
  params: {
    category?: "delinquent" | "frequent";
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  },
  reason: string
): Promise<Blob> {
  const searchParams = new URLSearchParams({ export: "pdf" });
  searchParams.append("category", params.category ?? "delinquent");
  if (typeof params.limit === "number") {
    searchParams.append("limit", String(params.limit));
  }
  if (params.dateFrom) {
    searchParams.append("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.append("date_to", params.dateTo);
  }
  return request<Blob>(
    `/reports/customers/portfolio?${searchParams.toString()}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function exportCustomerPortfolioExcel(
  token: string,
  params: {
    category?: "delinquent" | "frequent";
    limit?: number;
    dateFrom?: string;
    dateTo?: string;
  },
  reason: string
): Promise<Blob> {
  const searchParams = new URLSearchParams({ export: "xlsx" });
  searchParams.append("category", params.category ?? "delinquent");
  if (typeof params.limit === "number") {
    searchParams.append("limit", String(params.limit));
  }
  if (params.dateFrom) {
    searchParams.append("date_from", params.dateFrom);
  }
  if (params.dateTo) {
    searchParams.append("date_to", params.dateTo);
  }
  return request<Blob>(
    `/reports/customers/portfolio?${searchParams.toString()}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function getCustomerDashboardMetrics(
  token: string,
  params: { months?: number; topLimit?: number } = {}
): Promise<CustomerDashboardMetrics> {
  const searchParams = new URLSearchParams();
  if (typeof params.months === "number") {
    searchParams.append("months", String(params.months));
  }
  if (typeof params.topLimit === "number") {
    searchParams.append("top_limit", String(params.topLimit));
  }
  const suffix = searchParams.toString();
  const query = suffix ? `?${suffix}` : "";
  return request<CustomerDashboardMetrics>(
    `/customers/dashboard${query}`,
    { method: "GET" },
    token
  );
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

export function appendCustomerNote(
  token: string,
  customerId: number,
  note: string,
  reason: string
): Promise<Customer> {
  return request<Customer>(
    `/customers/${customerId}/notes`,
    {
      method: "POST",
      body: JSON.stringify({ note }),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function registerCustomerPayment(
  token: string,
  customerId: number,
  payload: CustomerPaymentPayload,
  reason: string
): Promise<CustomerLedgerEntry> {
  return request<CustomerLedgerEntry>(
    `/customers/${customerId}/payments`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function getCustomerSummary(token: string, customerId: number): Promise<CustomerSummary> {
  return request<CustomerSummary>(
    `/customers/${customerId}/summary`,
    { method: "GET" },
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
  return requestCollection<Supplier>(`/suppliers?${params.toString()}`, { method: "GET" }, token);
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

export function getSupplierBatchOverview(
  token: string,
  storeId: number,
  limit = 5,
): Promise<SupplierBatchOverviewItem[]> {
  return requestCollection<SupplierBatchOverviewItem>(
    `/reports/inventory/supplier-batches?store_id=${storeId}&limit=${limit}`,
    { method: "GET" },
    token,
  );
}

export function listSupplierBatches(
  token: string,
  supplierId: number,
  limit = 50
): Promise<SupplierBatch[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestCollection<SupplierBatch>(
    `/suppliers/${supplierId}/batches?${params.toString()}`,
    { method: "GET" },
    token
  );
}

export function createSupplierBatch(
  token: string,
  supplierId: number,
  payload: SupplierBatchPayload,
  reason: string
): Promise<SupplierBatch> {
  return request<SupplierBatch>(
    `/suppliers/${supplierId}/batches`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateSupplierBatch(
  token: string,
  batchId: number,
  payload: Partial<SupplierBatchPayload>,
  reason: string
): Promise<SupplierBatch> {
  return request<SupplierBatch>(
    `/suppliers/batches/${batchId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function deleteSupplierBatch(token: string, batchId: number, reason: string): Promise<void> {
  return request<void>(
    `/suppliers/batches/${batchId}`,
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
  return requestCollection<RepairOrder>(`/repairs${suffix}`, { method: "GET" }, token);
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
  if (filters.categoria) params.append("categoria", filters.categoria);
  if (filters.condicion) params.append("condicion", filters.condicion);
  if (filters.estado) params.append("estado", filters.estado);
  if (filters.ubicacion) params.append("ubicacion", filters.ubicacion);
  if (filters.proveedor) params.append("proveedor", filters.proveedor);
  if (filters.fecha_ingreso_desde) params.append("fecha_ingreso_desde", filters.fecha_ingreso_desde);
  if (filters.fecha_ingreso_hasta) params.append("fecha_ingreso_hasta", filters.fecha_ingreso_hasta);
  const query = params.toString();
  const path = query ? `/inventory/devices/search?${query}` : "/inventory/devices/search";
  return requestCollection<CatalogDevice>(path, { method: "GET" }, token);
}

export function registerMovement(
  token: string,
  storeId: number,
  payload: MovementInput,
  comment: string
) {
  return request(`/inventory/stores/${storeId}/movements`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: { "X-Reason": comment },
  }, token);
}

export function listSales(token: string, filters: SalesFilters = {}): Promise<Sale[]> {
  const params = buildSalesFilterParams(filters);
  const limit = typeof filters.limit === "number" ? filters.limit : 50;
  params.append("limit", String(limit));
  const query = params.toString();
  const path = `/sales?${query}`;
  return requestCollection<Sale>(path, { method: "GET" }, token);
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

export function exportSalesPdf(token: string, filters: SalesFilters = {}, reason: string): Promise<Blob> {
  const params = buildSalesFilterParams(filters);
  const query = params.toString();
  const path = query ? `/sales/export/pdf?${query}` : "/sales/export/pdf";
  return request<Blob>(path, { method: "GET", headers: { "X-Reason": reason } }, token);
}

export function exportSalesExcel(token: string, filters: SalesFilters = {}, reason: string): Promise<Blob> {
  const params = buildSalesFilterParams(filters);
  const query = params.toString();
  const path = query ? `/sales/export/xlsx?${query}` : "/sales/export/xlsx";
  return request<Blob>(path, { method: "GET", headers: { "X-Reason": reason } }, token);
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
  return requestCollection<StoreMembership>(`/stores/${storeId}/memberships`, { method: "GET" }, token);
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
  const params = new URLSearchParams();
  params.set("limit", "25");
  if (typeof storeId === "number") {
    params.set("store_id", String(storeId));
  }
  const query = params.toString();
  const path = `/transfers${query ? `?${query}` : ""}`;
  return requestCollection<TransferOrder>(path, { method: "GET" }, token);
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

function buildTransferReportQuery(filters: TransferReportFilters = {}): string {
  const params = new URLSearchParams();
  if (typeof filters.store_id === "number") {
    params.set("store_id", String(filters.store_id));
  }
  if (typeof filters.origin_store_id === "number") {
    params.set("origin_store_id", String(filters.origin_store_id));
  }
  if (typeof filters.destination_store_id === "number") {
    params.set("destination_store_id", String(filters.destination_store_id));
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.date_from) {
    params.set("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.set("date_to", filters.date_to);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getTransferReport(
  token: string,
  filters: TransferReportFilters = {},
): Promise<TransferReport> {
  const query = buildTransferReportQuery(filters);
  return request<TransferReport>(`/transfers/report${query}`, { method: "GET" }, token);
}

export function exportTransferReportPdf(
  token: string,
  reason: string,
  filters: TransferReportFilters = {},
): Promise<Blob> {
  const query = buildTransferReportQuery(filters);
  return request<Blob>(
    `/transfers/export/pdf${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function exportTransferReportExcel(
  token: string,
  reason: string,
  filters: TransferReportFilters = {},
): Promise<Blob> {
  const query = buildTransferReportQuery(filters);
  return request<Blob>(
    `/transfers/export/xlsx${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function listRecurringOrders(
  token: string,
  orderType?: RecurringOrderType
): Promise<RecurringOrder[]> {
  const params = new URLSearchParams();
  if (orderType) {
    params.set("order_type", orderType);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<RecurringOrder>(
    `/operations/recurring-orders${suffix}`,
    { method: "GET" },
    token,
  );
}

export function createRecurringOrder(
  token: string,
  payload: RecurringOrderPayload,
  reason: string
): Promise<RecurringOrder> {
  return request<RecurringOrder>(
    "/operations/recurring-orders",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function executeRecurringOrder(
  token: string,
  templateId: number,
  reason: string
): Promise<RecurringOrderExecutionResult> {
  return request<RecurringOrderExecutionResult>(
    `/operations/recurring-orders/${templateId}/execute`,
    { method: "POST", headers: { "X-Reason": reason } },
    token
  );
}

export type OperationsHistoryFilters = {
  storeId?: number | null;
  technicianId?: number | null;
  startDate?: string;
  endDate?: string;
};

export function listOperationsHistory(
  token: string,
  filters: OperationsHistoryFilters = {}
): Promise<OperationsHistoryResponse> {
  const params = new URLSearchParams();
  if (filters.storeId != null) {
    params.set("store_id", String(filters.storeId));
  }
  if (filters.technicianId != null) {
    params.set("technician_id", String(filters.technicianId));
  }
  if (filters.startDate) {
    params.set("start_date", filters.startDate);
  }
  if (filters.endDate) {
    params.set("end_date", filters.endDate);
  }
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<OperationsHistoryResponse>(`/operations/history${suffix}`, { method: "GET" }, token);
}

export function triggerSync(token: string, storeId?: number) {
  return request(`/sync/run`, {
    method: "POST",
    body: JSON.stringify({ store_id: storeId ?? null }),
  }, token);
}

// [PACK35-frontend]
export function enqueueSyncQueueEvents(
  token: string,
  events: SyncQueueEventInput[],
): Promise<SyncQueueEnqueueResponse> {
  return request(`/sync/events`, { method: "POST", body: JSON.stringify({ events }) }, token);
}

// [PACK35-frontend]
export function dispatchSyncQueueEvents(
  token: string,
  limit = 25,
): Promise<SyncQueueDispatchResult> {
  const params = new URLSearchParams({ limit: String(limit) });
  return request(`/sync/dispatch?${params.toString()}`, { method: "POST" }, token);
}

// [PACK35-frontend]
export function listSyncQueueStatus(
  token: string,
  params: { limit?: number; status?: SyncQueueStatus } = {},
): Promise<SyncQueueEntry[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.status) {
    query.set("status_filter", params.status);
  }
  const suffix = query.toString();
  return request(`/sync/status${suffix ? `?${suffix}` : ""}`, { method: "GET" }, token);
}

// [PACK35-frontend]
export function resolveSyncQueueEvent(token: string, queueId: number): Promise<SyncQueueEntry> {
  return request(`/sync/resolve/${queueId}`, { method: "POST" }, token);
}

export function runBackup(token: string, reason: string, note?: string): Promise<BackupJob> {
  return request<BackupJob>("/backups/run", {
    method: "POST",
    body: JSON.stringify({ nota: note }),
    headers: {
      "X-Reason": reason,
    },
  }, token);
}

export function fetchBackupHistory(token: string): Promise<BackupJob[]> {
  return requestCollection<BackupJob>("/backups/history", { method: "GET" }, token);
}

export async function downloadInventoryPdf(token: string, reason: string): Promise<void> {
  const response = await fetch(`${API_URL}/reports/inventory/pdf`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
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

export async function downloadInventoryCsv(token: string, reason: string): Promise<void> {
  const response = await fetch(`${API_URL}/reports/inventory/csv`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el CSV");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_inventario.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryCurrentCsv(
  token: string,
  reason: string,
  filters: InventoryCurrentFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/current/csv${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar las existencias actuales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_existencias.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryCurrentPdf(
  token: string,
  reason: string,
  filters: InventoryCurrentFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/current/pdf${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar el PDF de existencias actuales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_existencias.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryCurrentXlsx(
  token: string,
  reason: string,
  filters: InventoryCurrentFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/current/xlsx${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar el Excel de existencias actuales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_existencias.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryValueCsv(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/value/csv${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar la valoración de inventario");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_valor_inventario.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryValuePdf(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/value/pdf${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF de valoración de inventario");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_valor_inventario.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryValueXlsx(
  token: string,
  reason: string,
  filters: InventoryValueFilters = {},
): Promise<void> {
  const params = buildInventoryValueParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/value/xlsx${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el Excel de valoración de inventario");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_valor_inventario.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryMovementsCsv(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/movements/csv${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar los movimientos de inventario");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_movimientos.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryMovementsPdf(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/movements/pdf${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF de movimientos");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_movimientos.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadInventoryMovementsXlsx(
  token: string,
  reason: string,
  filters: InventoryMovementsFilters = {},
): Promise<void> {
  const params = buildInventoryMovementsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/movements/xlsx${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el Excel de movimientos");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_movimientos.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadTopProductsCsv(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/top-products/csv${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible exportar los productos más vendidos");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_productos_populares.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadTopProductsPdf(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/top-products/pdf${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF de productos más vendidos");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_top_productos.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadTopProductsXlsx(
  token: string,
  reason: string,
  filters: InventoryTopProductsFilters = {},
): Promise<void> {
  const params = buildTopProductsParams(filters);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${API_URL}/reports/inventory/top-products/xlsx${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el Excel de productos más vendidos");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_top_productos.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getUpdateStatus(token: string): Promise<UpdateStatus> {
  return request<UpdateStatus>("/updates/status", { method: "GET" }, token);
}

export function getReleaseHistory(token: string, limit = 10): Promise<ReleaseInfo[]> {
  return requestCollection<ReleaseInfo>(`/updates/history?limit=${limit}`, { method: "GET" }, token);
}

export function getInventoryMetrics(token: string, lowStockThreshold = 5): Promise<InventoryMetrics> {
  return request<InventoryMetrics>(
    `/reports/metrics?low_stock_threshold=${lowStockThreshold}`,
    { method: "GET" },
    token
  );
}

export function getRotationAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsRotation> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsRotation>(`/reports/analytics/rotation${query}`, { method: "GET" }, token);
}

export function getAgingAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsAging> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsAging>(`/reports/analytics/aging${query}`, { method: "GET" }, token);
}

export function getForecastAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsForecast> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsForecast>(`/reports/analytics/stockout_forecast${query}`, { method: "GET" }, token);
}

export async function downloadAnalyticsPdf(
  token: string,
  reason: string,
  filters?: AnalyticsFilters,
): Promise<void> {
  const query = buildAnalyticsQuery(filters);
  const response = await fetch(`${API_URL}/reports/analytics/pdf${query}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
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

export async function downloadAnalyticsCsv(
  token: string,
  reason: string,
  filters?: AnalyticsFilters,
): Promise<void> {
  const query = buildAnalyticsQuery(filters);
  const response = await fetch(`${API_URL}/reports/analytics/export.csv${query}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
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

export type GlobalReportFilters = {
  dateFrom?: string;
  dateTo?: string;
  module?: string;
  severity?: SystemLogLevel;
};

function buildGlobalReportQuery(filters: GlobalReportFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.module) {
    params.set("module", filters.module);
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getGlobalReportOverview(
  token: string,
  filters: GlobalReportFilters = {},
): Promise<GlobalReportOverview> {
  const query = buildGlobalReportQuery(filters);
  return request<GlobalReportOverview>(`/reports/global/overview${query}`, { method: "GET" }, token);
}

export function getGlobalReportDashboard(
  token: string,
  filters: GlobalReportFilters = {},
): Promise<GlobalReportDashboard> {
  const query = buildGlobalReportQuery(filters);
  return request<GlobalReportDashboard>(`/reports/global/dashboard${query}`, { method: "GET" }, token);
}

export async function downloadGlobalReportPdf(
  token: string,
  reason: string,
  filters: GlobalReportFilters = {},
): Promise<void> {
  const query = buildGlobalReportQuery(filters);
  const suffix = query ? `${query}&format=pdf` : "?format=pdf";
  const response = await fetch(`${API_URL}/reports/global/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el PDF de reportes globales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_reporte_global.pdf";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadGlobalReportXlsx(
  token: string,
  reason: string,
  filters: GlobalReportFilters = {},
): Promise<void> {
  const query = buildGlobalReportQuery(filters);
  const suffix = query ? `${query}&format=xlsx` : "?format=xlsx";
  const response = await fetch(`${API_URL}/reports/global/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el Excel de reportes globales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_reporte_global.xlsx";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function downloadGlobalReportCsv(
  token: string,
  reason: string,
  filters: GlobalReportFilters = {},
): Promise<void> {
  const query = buildGlobalReportQuery(filters);
  const suffix = query ? `${query}&format=csv` : "?format=csv";
  const response = await fetch(`${API_URL}/reports/global/export${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Reason": reason,
    },
  });

  if (!response.ok) {
    throw new Error("No fue posible descargar el CSV de reportes globales");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "softmobile_reporte_global.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function getComparativeAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsComparative> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsComparative>(`/reports/analytics/comparative${query}`, { method: "GET" }, token);
}

export function getProfitMarginAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsProfitMargin> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsProfitMargin>(`/reports/analytics/profit_margin${query}`, { method: "GET" }, token);
}

export function getSalesProjectionAnalytics(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsSalesProjection> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsSalesProjection>(`/reports/analytics/sales_forecast${query}`, { method: "GET" }, token);
}

export function getAnalyticsCategories(token: string): Promise<AnalyticsCategories> {
  return request<AnalyticsCategories>("/reports/analytics/categories", { method: "GET" }, token);
}

export function getAnalyticsAlerts(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsAlerts> {
  const query = buildAnalyticsQuery(filters);
  return request<AnalyticsAlerts>(`/reports/analytics/alerts${query}`, { method: "GET" }, token);
}

export function getAnalyticsRealtime(
  token: string,
  filters?: AnalyticsFilters,
): Promise<AnalyticsRealtime> {
  const { storeIds, category } = filters ?? {};
  const query = buildAnalyticsQuery({ storeIds, category });
  return request<AnalyticsRealtime>(`/reports/analytics/realtime${query}`, { method: "GET" }, token);
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
  return requestCollection<ActiveSession>(`/security/sessions${query}`, { method: "GET" }, token);
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
  return requestCollection<SyncOutboxEntry>(`/sync/outbox${query}`, { method: "GET" }, token);
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
  return requestCollection<SyncOutboxStatsEntry>("/sync/outbox/stats", { method: "GET" }, token);
}

export function getSyncQueueSummary(token: string): Promise<SyncQueueSummary> {
  return request<SyncQueueSummary>("/sync/status/summary", { method: "GET" }, token);
} // [PACK35-frontend]

// [PACK35-frontend]
export function getSyncHybridBreakdown(
  token: string,
): Promise<SyncHybridModuleBreakdownItem[]> {
  return requestCollection<SyncHybridModuleBreakdownItem>(
    "/sync/status/breakdown",
    { method: "GET" },
    token,
  );
}

export function getSyncHybridProgress(token: string): Promise<SyncHybridProgress> {
  return request<SyncHybridProgress>("/sync/status/hybrid", { method: "GET" }, token);
} // [PACK35-frontend]

// [PACK35-frontend]
export function getSyncHybridForecast(
  token: string,
  lookbackMinutes?: number,
): Promise<SyncHybridForecast> {
  const search = typeof lookbackMinutes === "number" ? `?lookback_minutes=${lookbackMinutes}` : "";
  return request<SyncHybridForecast>(`/sync/status/forecast${search}`, { method: "GET" }, token);
} // [PACK35-frontend]

export function getSyncHistory(token: string, limitPerStore = 5): Promise<SyncStoreHistory[]> {
  return requestCollection<SyncStoreHistory>(
    `/sync/history?limit_per_store=${limitPerStore}`,
    { method: "GET" },
    token,
  );
}

export function getSyncOverview(token: string, storeId?: number): Promise<SyncBranchOverview[]> {
  const query = typeof storeId === "number" ? `?store_id=${storeId}` : "";
  return requestCollection<SyncBranchOverview>(`/sync/overview${query}`, { method: "GET" }, token);
}

function buildSyncConflictQuery(filters: SyncConflictFilters = {}): string {
  const params = new URLSearchParams();
  if (typeof filters.store_id === "number") {
    params.set("store_id", String(filters.store_id));
  }
  if (filters.date_from) {
    params.set("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.set("date_to", filters.date_to);
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  if (typeof filters.limit === "number") {
    params.set("limit", String(filters.limit));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listSyncConflicts(
  token: string,
  filters: SyncConflictFilters = {},
): Promise<SyncConflictLog[]> {
  const query = buildSyncConflictQuery(filters);
  return requestCollection<SyncConflictLog>(`/sync/conflicts${query}`, { method: "GET" }, token);
}

export function exportSyncConflictsPdf(
  token: string,
  reason: string,
  filters: SyncConflictFilters = {},
): Promise<Blob> {
  const query = buildSyncConflictQuery(filters);
  return request<Blob>(
    `/sync/conflicts/export/pdf${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

export function exportSyncConflictsExcel(
  token: string,
  reason: string,
  filters: SyncConflictFilters = {},
): Promise<Blob> {
  const query = buildSyncConflictQuery(filters);
  return request<Blob>(
    `/sync/conflicts/export/xlsx${query}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token,
  );
}

function buildAuditQuery(filters: AuditLogFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.limit) {
    params.set("limit", String(filters.limit));
  }
  if (filters.action) {
    params.set("action", filters.action);
  }
  if (filters.entity_type) {
    params.set("entity_type", filters.entity_type);
  }
  if (typeof filters.performed_by_id === "number") {
    params.set("performed_by_id", String(filters.performed_by_id));
  }
  if (filters.date_from) {
    params.set("date_from", filters.date_from);
  }
  if (filters.date_to) {
    params.set("date_to", filters.date_to);
  }
  return params.toString();
}

export function getAuditLogs(token: string, filters: AuditLogFilters = {}): Promise<AuditLogEntry[]> {
  const query = buildAuditQuery(filters);
  const suffix = query ? `?${query}` : "";
  return requestCollection<AuditLogEntry>(`/audit/logs${suffix}`, { method: "GET" }, token);
}

export function exportAuditLogsCsv(
  token: string,
  filters: AuditLogFilters = {},
  reason = "Descarga auditoría"
): Promise<Blob> {
  const query = buildAuditQuery(filters);
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/audit/logs/export.csv${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function downloadAuditPdf(
  token: string,
  filters: AuditLogFilters = {},
  reason = "Reporte auditoría"
): Promise<Blob> {
  const query = buildAuditQuery(filters);
  const suffix = query ? `?${query}` : "";
  return request<Blob>(
    `/reports/audit/pdf${suffix}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function getAuditReminders(token: string): Promise<AuditReminderSummary> {
  return request<AuditReminderSummary>("/audit/reminders", { method: "GET" }, token);
}

export function acknowledgeAuditAlert(
  token: string,
  payload: AuditAcknowledgementInput,
  reason: string
): Promise<AuditAcknowledgementResponse> {
  return request<AuditAcknowledgementResponse>(
    "/audit/acknowledgements",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
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
  return requestCollection<CashSession>(`/pos/cash/history?${params.toString()}`, { method: "GET" }, token);
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
