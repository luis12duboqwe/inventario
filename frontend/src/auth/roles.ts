// [PACK26-ROLES-DEF-START]
export type Role = "ADMIN" | "GERENTE" | "OPERADOR" | "INVITADO";

// Catálogo de permisos (granular; UI)
export const PERMS = {
  // Ventas POS
  POS_VIEW: "sales.pos.view",
  POS_CHECKOUT: "sales.pos.checkout",
  POS_DISCOUNT: "sales.pos.discount",
  POS_PRICE_OVERRIDE: "sales.pos.priceOverride",
  POS_HOLD: "sales.pos.hold",
  POS_RESUME: "sales.pos.resume",
  POS_REFUND: "sales.pos.refund",

  // Cotizaciones
  QUOTE_LIST: "sales.quote.list",
  QUOTE_CREATE: "sales.quote.create",
  QUOTE_EDIT: "sales.quote.edit",
  QUOTE_CONVERT: "sales.quote.convert",

  // Devoluciones
  RETURN_LIST: "sales.return.list",
  RETURN_CREATE: "sales.return.create",
  RETURN_VIEW: "sales.return.view",

  // Clientes
  CUSTOMER_LIST: "sales.customer.list",
  CUSTOMER_CREATE: "sales.customer.create",
  CUSTOMER_EDIT: "sales.customer.edit",

  // Caja
  CASH_CLOSE: "sales.cash.close",

  // Auditoría
  AUDIT_VIEW: "audit.view",
} as const;

export type Perm = (typeof PERMS)[keyof typeof PERMS];

// Matriz por rol (UI). Ajusta a tus políticas reales.
export const ROLE_MATRIX: Record<Role, Perm[]> = {
  ADMIN: [
    PERMS.POS_VIEW, PERMS.POS_CHECKOUT, PERMS.POS_DISCOUNT, PERMS.POS_PRICE_OVERRIDE,
    PERMS.POS_HOLD, PERMS.POS_RESUME, PERMS.POS_REFUND,
    PERMS.QUOTE_LIST, PERMS.QUOTE_CREATE, PERMS.QUOTE_EDIT, PERMS.QUOTE_CONVERT,
    PERMS.RETURN_LIST, PERMS.RETURN_CREATE, PERMS.RETURN_VIEW,
    PERMS.CUSTOMER_LIST, PERMS.CUSTOMER_CREATE, PERMS.CUSTOMER_EDIT,
    PERMS.CASH_CLOSE,
    PERMS.AUDIT_VIEW
  ],
  GERENTE: [
    PERMS.POS_VIEW, PERMS.POS_CHECKOUT, PERMS.POS_DISCOUNT, PERMS.POS_PRICE_OVERRIDE,
    PERMS.POS_HOLD, PERMS.POS_RESUME,
    PERMS.QUOTE_LIST, PERMS.QUOTE_CREATE, PERMS.QUOTE_EDIT, PERMS.QUOTE_CONVERT,
    PERMS.RETURN_LIST, PERMS.RETURN_CREATE, PERMS.RETURN_VIEW,
    PERMS.CUSTOMER_LIST, PERMS.CUSTOMER_CREATE, PERMS.CUSTOMER_EDIT,
    PERMS.CASH_CLOSE,
    PERMS.AUDIT_VIEW
  ],
  OPERADOR: [
    PERMS.POS_VIEW, PERMS.POS_CHECKOUT,
    PERMS.POS_HOLD, PERMS.POS_RESUME,
    PERMS.QUOTE_LIST, PERMS.QUOTE_CREATE,
    PERMS.RETURN_LIST, PERMS.RETURN_CREATE,
    PERMS.CUSTOMER_LIST, PERMS.CUSTOMER_CREATE,
  ],
  INVITADO: [
    PERMS.POS_VIEW,
    PERMS.QUOTE_LIST,
    PERMS.RETURN_LIST,
    PERMS.CUSTOMER_LIST,
  ],
};
// [PACK26-ROLES-DEF-END]
