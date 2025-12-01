import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listSales, createSale, type SaleCreateInput, clearRequestCache } from "./api";

// Pruebas específicas de invalidación de caché para el módulo de ventas.
// Objetivo: asegurar que después de registrar una venta (POST /sales) se limpie la caché
// y la siguiente consulta GET /sales fuerce un nuevo fetch devolviendo datos actualizados.

describe("invalidación de caché en ventas tras operaciones mutables", () => {
  const originalFetch = globalThis.fetch;
  const token = "token-demo-ventas";

  beforeEach(() => {
    clearRequestCache();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = originalFetch;
    clearRequestCache();
  });

  it("limpia caché después de createSale y vuelve a pedir listado actualizado", async () => {
    const emptyList: Array<Record<string, unknown>> = [];
    const saleResponse = {
      id: 101,
      store_id: 1,
      total_amount: 2500,
      subtotal_amount: 2155,
      tax_amount: 345,
      discount_percent: 0,
      payment_method: "EFECTIVO",
      created_at: "2025-11-06T21:15:00Z",
      items: [
        { device_id: 501, quantity: 1, unit_price: 2500, id: 9001 },
      ],
    } as const;
    const updatedList = [saleResponse];

    const fetchMock = vi
      .fn()
      // Primer GET /sales
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(emptyList),
        blob: vi.fn(),
        text: vi.fn(),
      }))
      // POST /sales
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(saleResponse),
        blob: vi.fn(),
        text: vi.fn(),
      }))
      // Segundo GET /sales (debe re-ejecutarse tras invalidar caché)
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(updatedList),
        blob: vi.fn(),
        text: vi.fn(),
      }));

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    // Primer listado: cachea respuesta
    const initial = await listSales(token, { limit: 50 });
    expect(initial).toEqual(emptyList);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Registrar venta (POST) — debe limpiar caché interna
    const payload: SaleCreateInput = {
      store_id: 1,
      payment_method: "EFECTIVO",
      items: [{ device_id: 501, quantity: 1 }],
      discount_percent: 0,
    };
    const created = await createSale(token, payload, "Venta mostrador test");
    expect(created.id).toBe(101);
    expect(fetchMock).toHaveBeenCalledTimes(2); // GET + POST

    // Nuevo listado: debe forzar fetch y reflejar venta creada
    const after = await listSales(token, { limit: 50 });
    expect(after).toEqual(updatedList);
    expect(after.length).toBe(1);
    expect(fetchMock).toHaveBeenCalledTimes(3); // GET inicial, POST, nuevo GET tras invalidación
  });
});
