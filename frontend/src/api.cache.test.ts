import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearRequestCache, getStores, listUsers, registerMovement, type MovementInput } from "./api";

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
    const payload = [
      {
        id: 1,
        name: "Central",
        status: "activa",
        code: "SUC-001",
        timezone: "America/Mexico_City",
        inventory_value: 1000,
        created_at: "2025-10-25T10:00:00Z",
      },
    ];

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
    expect(first).toEqual(payload);
    expect(second).toEqual(payload);
    expect(first).not.toBe(second);
  });

  it("permite abortar una solicitud sin cancelar otras con señales distintas", async () => {
    const payload = [
      {
        id: 1,
        username: "admin",
        roles: ["admin"],
        is_active: true,
      },
    ];

    type Pending = { release: () => void };
    const pendingResponses: Pending[] = [];

    const fetchMock = vi.fn().mockImplementation((_: string, init?: RequestInit) => {
      return new Promise<Response>((resolve, reject) => {
        const signal = init?.signal as AbortSignal | undefined;
        if (signal) {
          signal.addEventListener("abort", () => {
            const abortError = new Error("La solicitud fue abortada");
            abortError.name = "AbortError";
            reject(abortError);
          });
        }

        pendingResponses.push({
          release: () =>
            resolve({
              ok: true,
              status: 200,
              headers: new Headers({ "content-type": "application/json" }),
              json: vi.fn().mockResolvedValue(payload),
              blob: vi.fn(),
              text: vi.fn(),
            } as unknown as Response),
        });
      });
    });

    global.fetch = fetchMock as unknown as typeof fetch;

    const controllerA = new AbortController();
    const controllerB = new AbortController();

    const firstPromise = listUsers(token, {}, { signal: controllerA.signal });
    const secondPromise = listUsers(token, {}, { signal: controllerB.signal });

    expect(fetchMock).toHaveBeenCalledTimes(2);

    controllerA.abort();

    await expect(firstPromise).rejects.toMatchObject({ name: "AbortError" });

    if (pendingResponses.length < 2) {
      throw new Error("Faltan respuestas simuladas para completar la prueba");
    }

    pendingResponses[1].release();

    const second = await secondPromise;
    expect(second).toEqual(payload);
  });

  it("reutiliza la respuesta cacheada para solicitudes GET equivalentes", async () => {
    const payload = [
      {
        id: 1,
        name: "Central",
        status: "activa",
        code: "SUC-001",
        timezone: "America/Mexico_City",
        inventory_value: 1000,
        created_at: "2025-10-25T10:00:00Z",
      },
    ];

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
    expect(first).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const second = await getStores(token);
    expect(second).toEqual(payload);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("invalida la caché cuando se ejecuta una operación mutable", async () => {
    const initialStores = [
      {
        id: 1,
        name: "Central",
        status: "activa",
        code: "SUC-001",
        timezone: "America/Mexico_City",
        inventory_value: 1000,
        created_at: "2025-10-25T10:00:00Z",
      },
    ];
    const updatedStores = [
      {
        id: 2,
        name: "Norte",
        status: "activa",
        code: "SUC-002",
        timezone: "America/Mexico_City",
        inventory_value: 1500,
        created_at: "2025-10-26T12:00:00Z",
      },
    ];

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
    expect(first).toEqual(initialStores);

    const movement: MovementInput = {
      producto_id: 99,
      tipo_movimiento: "entrada",
      cantidad: 5,
      comentario: "Reabastecimiento de prueba",
    };

    await registerMovement(token, 1, movement, "Reabastecimiento autorizado");

    const second = await getStores(token);
    expect(second).toEqual(updatedStores);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
