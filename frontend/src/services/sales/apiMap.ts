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
    price:      (saleId: string | number) => `${ROOT}/pos/sales/${saleId}/price`,           // POST CheckoutRequest -> Totals (simula totales)
    hold:       (saleId: string | number) => `${ROOT}/pos/sales/${saleId}/hold`,             // POST -> {holdId}
    resume:     (saleId: string | number) => `${ROOT}/pos/sales/${saleId}/resume`,           // POST
    checkout:   (saleId: string | number) => `${ROOT}/pos/sales/${saleId}/checkout`,         // POST CheckoutRequest -> CheckoutResponse
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
  }
} as const;

export type ApiMap = typeof apiMap;
