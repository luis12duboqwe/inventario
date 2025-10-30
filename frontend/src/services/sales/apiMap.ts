// src/services/sales/apiMap.ts
// Mapa de endpoints del backend. Ajusta los paths a tu FastAPI real.
// Puedes versionar: const ROOT = "/api/v1"; si tu backend usa ese prefijo.
const ROOT = "/api";

export const apiMap = {
  products: {
    search:     `${ROOT}/products/search`,               // GET ?q=&sku=&imei=...
    byId:       (id: string) => `${ROOT}/products/${id}`,
  },
  pos: {
    price:      `${ROOT}/sales/price`,                   // POST CheckoutRequest -> Totals (simula totales)
    hold:       `${ROOT}/sales/hold`,                    // POST -> {holdId}
    resume:     (holdId: string) => `${ROOT}/sales/hold/${holdId}`, // GET
    checkout:   `${ROOT}/sales/checkout`,                // POST CheckoutRequest -> CheckoutResponse
  },
  quotes: {
    list:       `${ROOT}/quotes`,                        // GET
    create:     `${ROOT}/quotes`,                        // POST
    byId:       (id: string) => `${ROOT}/quotes/${id}`,  // GET/PUT
    convert:    (id: string) => `${ROOT}/quotes/${id}/convert`, // POST -> CheckoutResponse
  },
  returns: {
    list:       `${ROOT}/returns`,                       // GET
    create:     `${ROOT}/returns`,                       // POST
    byId:       (id: string) => `${ROOT}/returns/${id}`, // GET
  },
  customers: {
    list:       `${ROOT}/customers`,                     // GET
    create:     `${ROOT}/customers`,                     // POST
    byId:       (id: string) => `${ROOT}/customers/${id}`, // GET/PUT
  },
  cash: {
    summary:    `${ROOT}/cash/summary`,                  // GET ?date=YYYY-MM-DD
    close:      `${ROOT}/cash/close`,                    // POST
  },
  // [PACK26-AUDIT-APIMAP-START]
  audit: {
    bulk: `${ROOT}/audit/ui/bulk`,
    list: `${ROOT}/audit/ui`,
    export: `${ROOT}/audit/ui/export`,
  } as any,
  // [PACK26-AUDIT-APIMAP-END]
} as const;

export type ApiMap = typeof apiMap;
