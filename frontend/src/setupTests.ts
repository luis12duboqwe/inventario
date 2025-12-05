import "@testing-library/jest-dom";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

// Silenciar avisos ruidosos no bloqueantes en pruebas (Router v7 flags y navegación jsdom)
const originalWarn = console.warn.bind(console);
const originalError = console.error.bind(console);

function includesAny(msg: string, variants: string[]): boolean {
  const lower = msg.toLowerCase();
  return variants.some((v) => lower.includes(v.toLowerCase()));
}

console.warn = ((...args: unknown[]) => {
  const first = String(args[0] ?? "");
  if (includesAny(first, [
    "React Router Future Flag Warning",
  ])) {
    return; // suprimir aviso informativo
  }
  return originalWarn(...args as []);
}) as typeof console.warn;

console.error = ((...args: unknown[]) => {
  const first = String(args[0] ?? "");
  if (includesAny(first, [
    "Not implemented: navigation to another Document",
    "Not implemented: navigation to another document",
  ])) {
    return; // suprimir error no implementado de jsdom durante descargas/navegaciones simuladas
  }
  return originalError(...args as []);
}) as typeof console.error;

class ResizeObserverMock implements ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {
    void _callback; // evitar warning por parámetro no usado
  }
  observe(): void { /* mock */ }
  unobserve(): void { /* mock */ }
  disconnect(): void { /* mock */ }
  takeRecords(): ResizeObserverEntry[] {
    return [];
  }
}

if (!("ResizeObserver" in globalThis)) {
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
}
