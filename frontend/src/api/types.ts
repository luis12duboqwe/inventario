export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  has_next: boolean;
};

export type SystemLogLevel = "info" | "warning" | "error" | "critical";

export type Role = {
  id: number;
  name: string;
};

export type ContactHistoryEntry = {
  timestamp: string;
  note: string;
};

export type ReturnDisposition = "vendible" | "defectuoso" | "no_vendible" | "reparacion";
export type ReturnReasonCategory = "defecto" | "logistica" | "cliente" | "precio" | "otro";

export type PaymentMethod =
  | "EFECTIVO"
  | "TARJETA"
  | "TRANSFERENCIA"
  | "OTRO"
  | "CREDITO"
  | "NOTA_CREDITO";

export type CashRegisterEntry = {
  id: number;
  session_id: number;
  entry_type: "INGRESO" | "EGRESO";
  amount: number;
  reason: string;
  notes?: string | null;
  created_by_id?: number | null;
  created_at: string;
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
  denomination_breakdown: Record<string, number>;
  reconciliation_notes?: string | null;
  difference_reason?: string | null;
  notes?: string | null;
  opened_by_id?: number | null;
  closed_by_id?: number | null;
  opened_at: string;
  closed_at?: string | null;
  entries?: CashRegisterEntry[] | null;
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

export type Credentials = {
  username: string;
  password: string;
  otp?: string;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
};

export type AuthProfile = {
  id: number;
  name: string;
  email?: string | null;
  role: string;
  roles: Role[];
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
