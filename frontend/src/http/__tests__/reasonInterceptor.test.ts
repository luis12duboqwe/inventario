import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";

import { applyReasonHeader } from "../reasonInterceptor";
import { clearStoredReason, rememberReason } from "../../utils/reasonStorage";

const STORAGE_KEY = "softmobile:last-x-reason";

describe("applyReasonHeader", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    const sessionStorage = {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
      removeItem: (key: string) => {
        store.delete(key);
      },
      clear: () => {
        store.clear();
      },
      key: (index: number) => Array.from(store.keys())[index] ?? null,
      length: 0,
    } as unknown as Storage;

    Object.defineProperty(sessionStorage, "length", {
      get() {
        return store.size;
      },
    });

    vi.stubGlobal("window", { sessionStorage } as unknown as Window & typeof globalThis);
    clearStoredReason();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("no altera peticiones fuera de los prefijos sensibles", () => {
    const headers = new Headers();
    applyReasonHeader("/inventory/items", "GET", headers);
    expect(headers.has("X-Reason")).toBe(false);
  });

  it("agrega un motivo por defecto para consultas GET", () => {
    const headers = new Headers();
    applyReasonHeader("/customers", "GET", headers);
    expect(headers.get("X-Reason")).toBe("Consulta clientes corporativa");
  });

  it("reutiliza el motivo almacenado cuando existe", () => {
    rememberReason("Consulta previa");
    const headers = new Headers();
    applyReasonHeader("/reports/analytics", "GET", headers);
    expect(headers.get("X-Reason")).toBe("Consulta previa");
  });

  it("propaga el motivo proporcionado y lo normaliza", () => {
    const headers = new Headers({ "X-Reason": "   Motivo directo   " });
    applyReasonHeader("/pos/sale", "POST", headers);
    expect(headers.get("X-Reason")).toBe("Motivo directo");
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBe("Motivo directo");
  });

  it("lanza error cuando falta el motivo en operaciones criticas", () => {
    const headers = new Headers();
    expect(() => applyReasonHeader("/pos/sale", "POST", headers)).toThrow(
      /motivo corporativo valido/i,
    );
  });
});
