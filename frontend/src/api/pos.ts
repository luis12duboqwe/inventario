import { request, requestCollection, API_URL } from "./client";
import { PaymentMethod, CashSession, CashRegisterEntry } from "./types";
import { Sale } from "./sales";
import { CustomerDebtSnapshot, CreditScheduleEntry, CustomerPaymentReceipt } from "./customers";

export type PosCartItemInput = {
  device_id?: number;
  productId?: number;
  imei?: string;
  quantity?: number;
  qty?: number;
  discount_percent?: number;
  discount?: number;
  price?: number | string;
  taxCode?: string;
};

export type PaymentBreakdown = Partial<Record<PaymentMethod, number>>;

export type PosSalePaymentEntry = {
  method: PaymentMethod | string;
  amount: number;
  reference?: string;
  tipAmount?: number;
  terminalId?: string;
  token?: string;
  metadata?: Record<string, string>;
};

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
  payments?: PosSalePaymentEntry[];
  branchId?: number;
  sessionId?: number;
  note?: string;
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
  receipt_pdf_base64?: string | null;
  debt_summary?: CustomerDebtSnapshot | null;
  credit_schedule?: CreditScheduleEntry[];
  debt_receipt_pdf_base64?: string | null;
  payment_receipts?: CustomerPaymentReceipt[];
};

export type PosConnectorType = "usb" | "network";

export type PosPrinterMode = "thermal" | "fiscal";

export type PosConnectorSettings = {
  type: PosConnectorType;
  identifier: string;
  path?: string | null;
  host?: string | null;
  port?: number | null;
};

export type PosPrinterSettings = {
  name: string;
  mode: PosPrinterMode;
  connector: PosConnectorSettings;
  paper_width_mm?: number | null;
  is_default: boolean;
  vendor?: string | null;
  supports_qr?: boolean;
};

export type PosCashDrawerSettings = {
  enabled: boolean;
  connector?: PosConnectorSettings | null;
  auto_open_on_cash_sale: boolean;
  pulse_duration_ms: number;
};

export type PosCustomerDisplaySettings = {
  enabled: boolean;
  channel: "websocket" | "local";
  brightness: number;
  theme: "dark" | "light";
  message_template?: string | null;
};

export type PosHardwareSettings = {
  printers: PosPrinterSettings[];
  cash_drawer: PosCashDrawerSettings;
  customer_display: PosCustomerDisplaySettings;
};

export type PosTerminalConfig = {
  id: string;
  label: string;
  adapter: string;
  currency: string;
};

export type PosConfig = {
  store_id: number;
  tax_rate: number;
  invoice_prefix: string;
  printer_name?: string | null;
  printer_profile?: string | null;
  quick_product_ids: number[];
  hardware_settings: PosHardwareSettings;
  updated_at: string;
  terminals: PosTerminalConfig[];
  tip_suggestions: number[];
};

export type PosConfigUpdateInput = {
  store_id: number;
  tax_rate: number;
  invoice_prefix: string;
  printer_name?: string | null;
  printer_profile?: string | null;
  quick_product_ids: number[];
  hardware_settings?: PosHardwareSettings;
};

export type PosSessionSummary = {
  session_id: number;
  branch_id: number;
  status: CashSession["status"];
  opened_at: string;
  closing_at?: string | null;
  opening_amount?: number | null;
  closing_amount?: number | null;
  expected_amount?: number | null;
  difference_amount?: number | null;
  payment_breakdown: Record<string, number>;
};

export type PosSessionOpenInput = {
  branchId: number;
  openingAmount: number;
  notes?: string;
};

export type PosSessionCloseInput = {
  sessionId: number;
  closingAmount: number;
  notes?: string;
  payments?: Record<string, number>;
};

export type PosTaxInfo = {
  code: string;
  name: string;
  rate: number;
};

export type PosSaleItemRequest = {
  productId?: number;
  device_id?: number;
  imei?: string;
  qty: number;
  price?: number | string;
  discount?: number;
  taxCode?: string;
};

export type PosSaleOperationPayload = {
  branchId: number;
  sessionId?: number;
  customerId?: number;
  customerName?: string;
  note?: string;
  confirm?: boolean;
  items: PosSaleItemRequest[];
  payments: PosSalePaymentEntry[];
};

export type PosReturnPayload = {
  originalSaleId: number;
  reason?: string;
  items: Array<{
    productId?: number;
    imei?: string;
    qty: number;
  }>;
};

export type PosReturnResponse = {
  sale_id: number;
  return_ids: number[];
  notes?: string | null;
};

export type PosSaleDetailResponse = {
  sale: Sale;
  receipt_url: string;
  receipt_pdf_base64?: string | null;
  debt_summary?: CustomerDebtSnapshot | null;
  credit_schedule?: CreditScheduleEntry[];
  debt_receipt_pdf_base64?: string | null;
  payment_receipts?: CustomerPaymentReceipt[];
};

export type PosHardwareActionResponse = {
  status: "queued" | "ok" | "error";
  message: string;
  details?: Record<string, unknown> | null;
};

export type PosHardwarePrintTestInput = {
  store_id: number;
  printer_name?: string | null;
  mode?: PosPrinterMode;
  sample?: string;
};

export type PosHardwareDrawerOpenInput = {
  store_id: number;
  connector_identifier?: string | null;
  pulse_duration_ms?: number | null;
};

export type PosHardwareDisplayPushInput = {
  store_id: number;
  headline: string;
  message?: string | null;
  total_amount?: number | null;
};

export type CashDenominationInput = {
  value: number;
  quantity: number;
};

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

export function submitPosSaleOperation(
  token: string,
  payload: PosSaleOperationPayload,
  reason: string
): Promise<PosSaleResponse> {
  const primaryMethod = (payload.payments[0]?.method as PaymentMethod) ?? "EFECTIVO";
  const bodyPayload = {
    branchId: payload.branchId,
    store_id: payload.branchId,
    sessionId: payload.sessionId,
    cash_session_id: payload.sessionId,
    customer_id: payload.customerId,
    customer_name: payload.customerName,
    note: payload.note,
    notes: payload.note,
    confirm: payload.confirm ?? true,
    payment_method: primaryMethod,
    payments: payload.payments.map((payment) => ({
      method: payment.method,
      amount: payment.amount,
    })),
    items: payload.items.map((item) => ({
      productId: item.productId ?? item.device_id,
      device_id: item.productId ?? item.device_id,
      imei: item.imei,
      qty: item.qty,
      quantity: item.qty,
      price: item.price,
      discount: item.discount,
      taxCode: item.taxCode,
    })),
  };

  return request<PosSaleResponse>(
    "/pos/sale",
    {
      method: "POST",
      body: JSON.stringify(bodyPayload),
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

export function testPosPrinter(
  token: string,
  payload: PosHardwarePrintTestInput,
  reason = "Prueba hardware POS"
): Promise<PosHardwareActionResponse> {
  return request<PosHardwareActionResponse>(
    "/pos/hardware/print-test",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function openPosCashDrawer(
  token: string,
  payload: PosHardwareDrawerOpenInput,
  reason = "Apertura manual gaveta"
): Promise<PosHardwareActionResponse> {
  return request<PosHardwareActionResponse>(
    "/pos/hardware/drawer/open",
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "X-Reason": reason },
    },
    token
  );
}

export function pushCustomerDisplay(
  token: string,
  payload: PosHardwareDisplayPushInput,
  reason = "Mensaje pantalla cliente"
): Promise<PosHardwareActionResponse> {
  return request<PosHardwareActionResponse>(
    "/pos/hardware/display/push",
    {
      method: "POST",
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
  payload: {
    session_id: number;
    closing_amount: number;
    payment_breakdown?: Record<string, number>;
    notes?: string;
    denominations?: CashDenominationInput[];
    reconciliation_notes?: string;
    difference_reason?: string;
  },
  reason: string
): Promise<CashSession> {
  return request<CashSession>(
    "/pos/cash/close",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function openPosSession(
  token: string,
  payload: PosSessionOpenInput,
  reason: string
): Promise<PosSessionSummary> {
  const body = {
    branchId: payload.branchId,
    opening_amount: payload.openingAmount,
    notes: payload.notes,
  };
  return request<PosSessionSummary>(
    "/pos/sessions/open",
    { method: "POST", body: JSON.stringify(body), headers: { "X-Reason": reason } },
    token
  );
}

export function closePosSession(
  token: string,
  payload: PosSessionCloseInput,
  reason: string
): Promise<PosSessionSummary> {
  const body = {
    session_id: payload.sessionId,
    closing_amount: payload.closingAmount,
    notes: payload.notes,
    payments: payload.payments,
  };
  return request<PosSessionSummary>(
    "/pos/sessions/close",
    { method: "POST", body: JSON.stringify(body), headers: { "X-Reason": reason } },
    token
  );
}

export function getLastPosSession(
  token: string,
  branchId: number,
  reason: string
): Promise<PosSessionSummary> {
  return request<PosSessionSummary>(
    `/pos/sessions/last?branchId=${branchId}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function listPosTaxes(
  token: string,
  reason: string
): Promise<PosTaxInfo[]> {
  return requestCollection<PosTaxInfo>(
    "/pos/taxes",
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function getPosSaleDetail(
  token: string,
  saleId: number,
  reason: string
): Promise<PosSaleDetailResponse> {
  return request<PosSaleDetailResponse>(
    `/pos/sale/${saleId}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function registerPosReturn(
  token: string,
  payload: PosReturnPayload,
  reason: string
): Promise<PosReturnResponse> {
  return request<PosReturnResponse>(
    "/pos/return",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listCashSessions(
  token: string,
  storeId: number,
  limit = 30,
  reason = "Consulta historial de caja"
): Promise<CashSession[]> {
  const params = new URLSearchParams({ store_id: String(storeId), limit: String(limit) });
  return requestCollection<CashSession>(
    `/pos/cash/history?${params.toString()}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function createCashRegisterEntry(
  token: string,
  payload: { session_id: number; entry_type: CashRegisterEntry["entry_type"]; amount: number; reason: string; notes?: string },
  reason: string
): Promise<CashRegisterEntry> {
  return request<CashRegisterEntry>(
    "/pos/cash/register/entries",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listCashRegisterEntries(
  token: string,
  sessionId: number,
  reason: string
): Promise<CashRegisterEntry[]> {
  return requestCollection<CashRegisterEntry>(
    `/pos/cash/register/entries?session_id=${sessionId}`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
}

export function getCashRegisterReport(
  token: string,
  sessionId: number,
  reason: string,
  exportFormat: "json" | "pdf" = "json"
): Promise<CashSession> | Promise<Blob> {
  if (exportFormat === "pdf") {
    return (async () => {
      const response = await fetch(`${API_URL}/pos/cash/register/${sessionId}/report?export=pdf`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Reason": reason,
        },
      });
      if (!response.ok) {
        throw new Error("No fue posible descargar el reporte en PDF");
      }
      return await response.blob();
    })();
  }
  return request<CashSession>(
    `/pos/cash/register/${sessionId}/report?export=json`,
    { method: "GET", headers: { "X-Reason": reason } },
    token
  );
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
