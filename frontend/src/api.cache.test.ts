import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearRequestCache, getStores, registerMovement, type MovementInput } from "./api";

describe("memoización de peticiones del SDK", () => {
  const originalFetch = global.fetch;
  const token = "token-demo-123456";

  beforeEach(() => {
    clearRequestCache();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
    clearRequestCache();
  });

  it("agrupa solicitudes GET simultáneas y evita duplicados", async () => {
    const payload = {
      items: [
        {
          id: 1,
          name: "Central",
          status: "activa",
          code: "SUC-001",
          timezone: "America/Mexico_City",
          inventory_value: 1000,
          created_at: "2025-10-25T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
      has_next: false,
    };

    let releaseResponse: (() => void) | null = null;
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          releaseResponse = () =>
            resolve({
              ok: true,
              status: 200,
              headers: new Headers({ "content-type": "application/json" }),
              json: vi.fn().mockResolvedValue(payload),
              blob: vi.fn(),
              text: vi.fn(),
            } as unknown as Response);
        }),
    );

    global.fetch = fetchMock as unknown as typeof fetch;

    const firstPromise = getStores(token);
    const secondPromise = getStores(token);

    if (!releaseResponse) {
      throw new Error("La promesa de fetch no fue inicializada");
    }

    releaseResponse();

    const [first, second] = await Promise.all([firstPromise, secondPromise]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(first).toEqual(payload.items);
    expect(second).toEqual(payload.items);
    expect(first).not.toBe(second);
  });

  it("reutiliza la respuesta cacheada para solicitudes GET equivalentes", async () => {
    const payload = {
      items: [
        {
          id: 1,
          name: "Central",
          status: "activa",
          code: "SUC-001",
          timezone: "America/Mexico_City",
          inventory_value: 1000,
          created_at: "2025-10-25T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
      has_next: false,
    };

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: vi.fn().mockResolvedValue(payload),
      blob: vi.fn(),
      text: vi.fn(),
    });

    global.fetch = fetchMock as unknown as typeof fetch;

    const first = await getStores(token);
    expect(first).toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const second = await getStores(token);
    expect(second).toEqual(payload.items);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("invalida la caché cuando se ejecuta una operación mutable", async () => {
    const initialStores = {
      items: [
        {
          id: 1,
          name: "Central",
          status: "activa",
          code: "SUC-001",
          timezone: "America/Mexico_City",
          inventory_value: 1000,
          created_at: "2025-10-25T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
      has_next: false,
    };
    const updatedStores = {
      items: [
        {
          id: 2,
          name: "Norte",
          status: "activa",
          code: "SUC-002",
          timezone: "America/Mexico_City",
          inventory_value: 1500,
          created_at: "2025-10-26T12:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
      has_next: false,
    };

    const fetchMock = vi.fn()
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(initialStores),
        blob: vi.fn(),
        text: vi.fn(),
      }))
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 204,
        headers: new Headers(),
        json: vi.fn(),
        blob: vi.fn(),
        text: vi.fn().mockResolvedValue(""),
      }))
      .mockImplementationOnce(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: vi.fn().mockResolvedValue(updatedStores),
        blob: vi.fn(),
        text: vi.fn(),
      }));

    global.fetch = fetchMock as unknown as typeof fetch;

    const first = await getStores(token);
    expect(first).toEqual(initialStores.items);

    const movement: MovementInput = {
      producto_id: 99,
      tipo_movimiento: "entrada",
      cantidad: 5,
      comentario: "Reabastecimiento de prueba",
    };

    await registerMovement(token, 1, movement, "Reabastecimiento autorizado");

    const second = await getStores(token);
    expect(second).toEqual(updatedStores.items);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
