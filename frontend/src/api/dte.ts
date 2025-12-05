import { request, requestCollection } from "./client";

export type DTEStatus = "borrador" | "generado" | "enviado" | "aceptado" | "rechazado" | "anulado";
export type DTEDispatchStatus = "pendiente" | "enviado" | "error" | "reintentando";

export type DTEAuthorization = {
  id: number;
  store_id: number;
  document_type: string;
  serie: string;
  cai: string;
  range_start: number;
  range_end: number;
  current_number: number;
  expiration_date: string;
  active: boolean;
  notes?: string;
  remaining: number;
  created_at: string;
  updated_at: string;
};

export type DTEAuthorizationCreatePayload = {
  store_id: number;
  document_type: string;
  cai: string;
  range_from: number;
  range_to: number;
  deadline: string;
};

export type DTEAuthorizationUpdatePayload = Partial<DTEAuthorizationCreatePayload> & {
  is_active?: boolean;
};

export type DTEDocument = {
  id: number;
  store_id: number;
  sale_id: number;
  document_type: string;
  cai: string;
  folio: string;
  sequence: number;
  issue_date: string;
  total_amount: number;
  tax_amount: number;
  status: DTEStatus;
  xml_content?: string | null;
  pdf_url?: string | null;
  created_at: string;
  updated_at: string;
  events: unknown[];
  queue: unknown[];
};

export type DTEGenerationRequest = {
  sale_id: number;
  document_type?: string;
};

export type DTEDispatchRequest = {
  destination_email?: string;
  include_xml?: boolean;
  include_pdf?: boolean;
};

export type DTEAckRegistration = {
  status: "aceptado" | "rechazado";
  message?: string;
  external_id?: string;
};

export type DTEDispatchQueueEntry = {
  id: number;
  document_id: number;
  status: DTEDispatchStatus;
  attempts: number;
  last_attempt_at?: string | null;
  next_attempt_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export function listDTEAuthorizations(
  token: string,
  params: { store_id?: number; document_type?: string; active?: boolean } = {}
): Promise<DTEAuthorization[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.store_id === "number") {
    searchParams.set("store_id", String(params.store_id));
  }
  if (params.document_type) {
    searchParams.set("document_type", params.document_type);
  }
  if (typeof params.active === "boolean") {
    searchParams.set("active", String(params.active));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<DTEAuthorization>(
    `/dte/authorizations${suffix}`,
    { method: "GET" },
    token
  );
}

export function createDTEAuthorization(
  token: string,
  payload: DTEAuthorizationCreatePayload,
  reason: string
): Promise<DTEAuthorization> {
  return request<DTEAuthorization>(
    "/dte/authorizations",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function updateDTEAuthorization(
  token: string,
  authorizationId: number,
  payload: DTEAuthorizationUpdatePayload,
  reason: string
): Promise<DTEAuthorization> {
  return request<DTEAuthorization>(
    `/dte/authorizations/${authorizationId}`,
    { method: "PUT", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function generateDTEDocument(
  token: string,
  payload: DTEGenerationRequest,
  reason: string
): Promise<DTEDocument> {
  return request<DTEDocument>(
    "/dte/documents/generate",
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listDTEDocuments(
  token: string,
  params: {
    store_id?: number;
    sale_id?: number;
    status?: DTEStatus;
    limit?: number;
    offset?: number;
  } = {}
): Promise<DTEDocument[]> {
  const searchParams = new URLSearchParams();
  if (typeof params.store_id === "number") {
    searchParams.set("store_id", String(params.store_id));
  }
  if (typeof params.sale_id === "number") {
    searchParams.set("sale_id", String(params.sale_id));
  }
  if (params.status) {
    searchParams.set("status", params.status);
  }
  if (typeof params.limit === "number") {
    searchParams.set("limit", String(params.limit));
  }
  if (typeof params.offset === "number") {
    searchParams.set("offset", String(params.offset));
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<DTEDocument>(`/dte/documents${suffix}`, { method: "GET" }, token);
}

export function getDTEDocument(token: string, documentId: number): Promise<DTEDocument> {
  return request<DTEDocument>(`/dte/documents/${documentId}`, { method: "GET" }, token);
}

export function sendDTEDocument(
  token: string,
  documentId: number,
  payload: DTEDispatchRequest,
  reason: string
): Promise<DTEDocument> {
  return request<DTEDocument>(
    `/dte/documents/${documentId}/send`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function acknowledgeDTEDocument(
  token: string,
  documentId: number,
  payload: DTEAckRegistration,
  reason: string
): Promise<DTEDocument> {
  return request<DTEDocument>(
    `/dte/documents/${documentId}/ack`,
    { method: "POST", body: JSON.stringify(payload), headers: { "X-Reason": reason } },
    token
  );
}

export function listDTEQueue(
  token: string,
  status?: DTEDispatchStatus
): Promise<DTEDispatchQueueEntry[]> {
  const searchParams = new URLSearchParams();
  if (status) {
    searchParams.set("status", status);
  }
  const query = searchParams.toString();
  const suffix = query ? `?${query}` : "";
  return requestCollection<DTEDispatchQueueEntry>(
    `/dte/queue${suffix}`,
    { method: "GET" },
    token
  );
}
