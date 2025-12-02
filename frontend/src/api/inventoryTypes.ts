import { TransferOrder } from "./transfers";
import {
  DashboardAuditAlerts,
} from "./audit";

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
  warehouse_id?: number | null;
  warehouse_name?: string | null;
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
  imeis_adicionales?: string[];
  imagenes?: string[];
  enlaces?: Array<{ titulo?: string | null; url: string }>;
  identifier?: DeviceIdentifier | null;
  variant_count?: number;
  has_variants?: boolean;
};

export type ProductVariant = {
  id: number;
  device_id: number;
  store_id: number;
  name: string;
  variant_sku: string;
  barcode?: string | null;
  unit_price_override?: number | null;
  is_default: boolean;
  is_active: boolean;
  device_sku: string;
  device_name: string;
  created_at: string;
  updated_at: string;
};

export type ProductVariantCreateInput = {
  name: string;
  variant_sku: string;
  barcode?: string | null;
  unit_price_override?: number | null;
  is_default?: boolean;
  is_active?: boolean;
};

export type ProductVariantUpdateInput = {
  name?: string | null;
  variant_sku?: string | null;
  barcode?: string | null;
  unit_price_override?: number | null;
  is_default?: boolean;
  is_active?: boolean;
};

export type ProductBundleItem = {
  id: number;
  device_id: number;
  variant_id?: number | null;
  quantity: number;
  device_sku: string;
  device_name: string;
  variant_name?: string | null;
};

export type ProductBundle = {
  id: number;
  store_id: number | null;
  name: string;
  bundle_sku: string;
  description?: string | null;
  base_price: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  items: ProductBundleItem[];
};

export type ProductBundleItemInput = {
  device_id: number;
  variant_id?: number | null;
  quantity?: number;
};

export type ProductBundleCreateInput = {
  store_id?: number | null;
  name: string;
  bundle_sku: string;
  description?: string | null;
  base_price?: number | null;
  is_active?: boolean;
  items: ProductBundleItemInput[];
};

export type ProductBundleUpdateInput = {
  store_id?: number | null;
  name?: string | null;
  bundle_sku?: string | null;
  description?: string | null;
  base_price?: number | null;
  is_active?: boolean;
  items?: ProductBundleItemInput[];
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
  imeis_adicionales?: string[];
  imagenes?: string[];
  enlaces?: Array<{ titulo?: string | null; url: string }>;
  completo?: boolean;
  warehouse_id?: number | null;
};

export type InventoryAvailabilityStore = {
  store_id: number;
  store_name: string;
  quantity: number;
};

export type InventoryAvailabilityRecord = {
  reference: string;
  sku?: string | null;
  product_name: string;
  device_ids: number[];
  total_quantity: number;
  stores: InventoryAvailabilityStore[];
};

export type InventoryAvailabilityResponse = {
  generated_at: string;
  items: InventoryAvailabilityRecord[];
};

export type Warehouse = {
  id: number;
  store_id: number;
  name: string;
  code: string;
  is_default: boolean;
  created_at: string;
};

export type WarehouseTransferInput = {
  store_id: number;
  device_id: number;
  quantity: number;
  source_warehouse_id: number;
  destination_warehouse_id: number;
  reason: string;
};

export type InventoryAvailabilityParams = {
  query?: string;
  skus?: string[];
  deviceIds?: number[];
  limit?: number;
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

export type InventoryMovement = {
  id: number;
  producto_id: number;
  tipo_movimiento: MovementInput["tipo_movimiento"];
  cantidad: number;
  comentario?: string | null;
  sucursal_origen_id?: number | null;
  sucursal_origen?: string | null;
  sucursal_destino_id?: number | null;
  sucursal_destino?: string | null;
  usuario_id?: number | null;
  usuario?: string | null;
  referencia_tipo?: string | null;
  referencia_id?: string | null;
  fecha: string;
  unit_cost?: number | null;
  store_inventory_value: number;
  ultima_accion?: unknown;
};

export type MovementResponse = InventoryMovement;

export type InventoryReservationState =
  | "RESERVADO"
  | "CONSUMIDO"
  | "CANCELADO"
  | "EXPIRADO";

export type InventoryReservation = {
  id: number;
  store_id: number;
  device_id: number;
  status: InventoryReservationState;
  initial_quantity: number;
  quantity: number;
  reason: string;
  resolution_reason?: string | null;
  reference_type?: string | null;
  reference_id?: string | null;
  expires_at: string;
  created_at: string;
  updated_at: string;
  reserved_by_id?: number | null;
  resolved_by_id?: number | null;
  resolved_at?: string | null;
  consumed_at?: string | null;
  device?: Device | null;
};

export type InventoryReservationInput = {
  store_id: number;
  device_id: number;
  quantity: number;
  expires_at: string;
};

export type InventoryReservationRenewInput = {
  expires_at: string;
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
  minimum_stock: number;
  reorder_point: number;
  reorder_gap?: number;
};

export type DashboardPoint = {
  label: string;
  value: number;
};

export type DashboardReceivableCustomer = {
  customer_id: number;
  name: string;
  outstanding_debt: number;
  available_credit?: number | null;
};

export type DashboardReceivableMetrics = {
  total_outstanding_debt: number;
  customers_with_debt: number;
  moroso_flagged: number;
  top_debtors: DashboardReceivableCustomer[];
};

export type DashboardSalesEntityMetric = {
  label: string;
  value: number;
  quantity?: number | null;
  percentage?: number | null;
};

export type DashboardSalesInsights = {
  average_ticket: number;
  top_products: DashboardSalesEntityMetric[];
  top_customers: DashboardSalesEntityMetric[];
  payment_mix: DashboardSalesEntityMetric[];
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
  sales_insights: DashboardSalesInsights;
  accounts_receivable: DashboardReceivableMetrics;
  sales_trend: DashboardPoint[];
  stock_breakdown: DashboardPoint[];
  repair_mix: DashboardPoint[];
  profit_breakdown: DashboardPoint[];
  audit_alerts: DashboardAuditAlerts;
};

export type InventoryAlertSeverity = "critical" | "warning" | "notice";

export type InventoryAlertItem = LowStockDevice & {
  severity: InventoryAlertSeverity;
  projected_days: number | null;
  average_daily_sales: number | null;
  trend: string | null;
  confidence: number | null;
  insights: string[];
};

export type InventoryAlertSummary = {
  total: number;
  critical: number;
  warning: number;
  notice: number;
};

export type InventoryAlertSettings = {
  threshold: number;
  minimum_threshold: number;
  maximum_threshold: number;
  warning_cutoff: number;
  critical_cutoff: number;
  adjustment_variance_threshold: number;
};

export type InventoryAlertsResponse = {
  settings: InventoryAlertSettings;
  summary: InventoryAlertSummary;
  items: InventoryAlertItem[];
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

export type DeviceListFilters = {
  search?: string;
  estado?: Device["estado_comercial"];
  categoria?: string;
  condicion?: string;
  estado_inventario?: string;
  ubicacion?: string;
  proveedor?: string;
  warehouse_id?: number | null;
  fecha_ingreso_desde?: string;
  fecha_ingreso_hasta?: string;
  limit?: number;
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

export type InventoryAuditFilters = {
  performedById?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
};

export type InventoryTopProductsFilters = InventoryCurrentFilters & {
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
};

export type InactiveProductsFilters = InventoryValueFilters & {
  minDaysWithoutMovement?: number;
  limit?: number;
  offset?: number;
};

export type SyncBranchHealth = "operativa" | "alerta" | "critica" | "sin_registros";

export type SyncConflictStoreDetail = {
  store_id: number;
  store_name: string;
  quantity: number;
};

export type SyncDiscrepancyLog = {
  id: number;
  sku: string;
  product_name?: string | null;
  detected_at: string;
  difference: number;
  severity: SyncBranchHealth;
  stores_max: SyncConflictStoreDetail[];
  stores_min: SyncConflictStoreDetail[];
};

export type SyncDiscrepancyFilters = {
  storeIds?: number[];
  dateFrom?: string;
  dateTo?: string;
  severity?: SyncDiscrepancyLog["severity"];
  minDifference?: number;
  limit?: number;
  offset?: number;
};

export type InventoryReceivingDistributionInput = {
  store_id: number;
  quantity: number;
};

export type InventoryReceivingLineInput = {
  device_id?: number;
  imei?: string;
  serial?: string;
  quantity: number;
  unit_cost?: number;
  comment?: string;
  distributions?: InventoryReceivingDistributionInput[];
};

export type InventoryReceivingRequest = {
  store_id: number;
  note: string;
  responsible?: string;
  reference?: string;
  lines: InventoryReceivingLineInput[];
};

export type InventoryReceivingProcessed = {
  identifier: string;
  device_id: number;
  quantity: number;
  movement: InventoryMovement;
};

export type InventoryReceivingResult = {
  store_id: number;
  processed: InventoryReceivingProcessed[];
  totals: { lines: number; total_quantity: number };
  auto_transfers?: TransferOrder[] | null;
};

export type InventoryCountLineInput = {
  device_id?: number;
  imei?: string;
  serial?: string;
  counted: number;
  comment?: string;
};

export type InventoryCycleCountRequest = {
  store_id: number;
  note: string;
  responsible?: string;
  reference?: string;
  lines: InventoryCountLineInput[];
};

export type InventoryCountDiscrepancy = {
  device_id: number;
  sku?: string | null;
  expected: number;
  counted: number;
  delta: number;
  identifier?: string | null;
  movement: InventoryMovement | null;
};

export type InventoryCycleCountResult = {
  store_id: number;
  adjustments: InventoryCountDiscrepancy[];
  totals: { lines: number; adjusted: number; matched: number; total_variance: number };
};

export type DeviceImportSummary = {
  created: number;
  updated: number;
  skipped: number;
  errors: Array<{ row: number; message: string }>;
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

export type InactiveProductEntry = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  device_name: string;
  categoria: string;
  quantity: number;
  valor_total_producto: number;
  ultima_venta: string | null;
  ultima_compra: string | null;
  ultimo_movimiento: string | null;
  dias_sin_movimiento: number | null;
  ventas_30_dias: number;
  ventas_90_dias: number;
  rotacion_30_dias: number;
  rotacion_90_dias: number;
  rotacion_total: number;
};

export type InactiveProductsTotals = {
  total_products: number;
  total_units: number;
  total_value: number;
  average_days_without_movement: number | null;
  max_days_without_movement: number | null;
};

export type InactiveProductsReport = {
  generated_at: string;
  filters: {
    store_ids: number[];
    categories: string[];
    min_days_without_movement: number;
  };
  totals: InactiveProductsTotals;
  items: InactiveProductEntry[];
};

export type SyncDiscrepancyTotals = {
  total_conflicts: number;
  warnings: number;
  critical: number;
  max_difference: number | null;
  affected_skus: number;
};

export type SyncDiscrepancyReport = {
  generated_at: string;
  filters: {
    store_ids: number[];
    date_from: string | null;
    date_to: string | null;
    severity: SyncDiscrepancyLog["severity"] | null;
    min_difference: number | null;
  };
  totals: SyncDiscrepancyTotals;
  items: SyncDiscrepancyLog[];
};

export type MinimumStockAlert = {
  store_id: number;
  store_name: string;
  device_id: number;
  sku: string;
  name: string;
  quantity: number;
  unit_price: number;
  minimum_stock: number;
  reorder_point: number;
  reorder_gap: number;
  inventory_value: number;
  below_minimum: boolean;
  below_reorder_point: boolean;
};

export type MinimumStockSummary = {
  total: number;
  below_minimum: number;
  below_reorder_point: number;
};

export type MinimumStockAlertsResponse = {
  summary: MinimumStockSummary;
  items: MinimumStockAlert[];
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
  estado_comercial?: Device["estado_comercial"];
  estado?: string;
  ubicacion?: string;
  proveedor?: string;
  fecha_ingreso_desde?: string;
  fecha_ingreso_hasta?: string;
};

export type DeviceLabelFormat = "pdf" | "zpl" | "escpos";
export type DeviceLabelTemplate = "38x25" | "50x30" | "80x50" | "a7";

export type LabelConnectorInput = {
  type?: "usb" | "network";
  identifier?: string;
  path?: string | null;
  host?: string | null;
  port?: number | null;
};

export type DeviceLabelDownload = {
  blob: Blob;
  filename: string;
};

export type DeviceLabelCommands = {
  format: Exclude<DeviceLabelFormat, "pdf">;
  template: DeviceLabelTemplate;
  commands: string;
  filename: string;
  content_type: string;
  connector?: LabelConnectorInput | null;
  message: string;
};
