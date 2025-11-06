import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listPurchaseRecords, createPurchaseRecord, type PurchaseRecordPayload, clearRequestCache } from "./api";

// Pruebas de invalidación de caché para registros de compras.
// Confirma que tras crear una compra (POST /purchases/records) se limpia la caché y
// la siguiente llamada GET /purchases/records obtiene datos nuevos.

describe("invalidación de caché en compras tras createPurchaseRecord", () => {
  const originalFetch = globalThis.fetch;
  const token = "token-demo-compras";

  beforeEach(() => {
    clearRequestCache();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = originalFetch;
    clearRequestCache();
  });

  it("re-fetch de registros después de POST crea compra y limpia caché", async () => {
    const emptyRecords: Array<Record<string, unknown>> = [];
    const purchaseRecord = {
      id_compra: 7001,
      proveedor_id: 88,
      proveedor_nombre: "Proveedor Demo",
      usuario_id: 1,
      usuario_nombre: "Usuario Demo",
      fecha: "2025-11-06T21:20:00Z",
      forma_pago: "TRANSFERENCIA",
      estado: "REGISTRADA",
      subtotal: 1000,
      impuesto: 160,
      total: 1160,
      items: [
        { id_detalle: 1, producto_id: 900, cantidad: 2, costo_unitario: 500, subtotal: 1000, producto_nombre: "Producto Demo" },
      ],
    } as const;
    const updated = [purchaseRecord];

    const fetchMock = vi
      .fn()
      // Primer GET /purchases/records
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(emptyRecords),
        blob: vi.fn(),
        text: vi.fn(),
      }))
      // POST /purchases/records
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(purchaseRecord),
        blob: vi.fn(),
        text: vi.fn(),
      }))
      // Segundo GET /purchases/records (debe ejecutarse tras invalidar caché)
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(updated),
        blob: vi.fn(),
        text: vi.fn(),
      }));

    globalThis.fetch = fetchMock as unknown as typeof fetch;

    // Primer listado cacheado
    const initial = await listPurchaseRecords(token, { limit: 50 });
    expect(initial).toEqual(emptyRecords);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    // Crear registro de compra (POST)
    const payload: PurchaseRecordPayload = {
      proveedor_id: 88,
      forma_pago: "TRANSFERENCIA",
      items: [{ producto_id: 900, cantidad: 2, costo_unitario: 500 }],
    };
    const created = await createPurchaseRecord(token, payload, "Registro compra test");
  expect(created.id_compra).toBe(7001);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    // Nuevo listado debe re-fetch y reflejar compra
    const after = await listPurchaseRecords(token, { limit: 50 });
    expect(after).toEqual(updated);
    expect(after.length).toBe(1);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
