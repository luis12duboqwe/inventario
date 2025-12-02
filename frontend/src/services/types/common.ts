// src/services/types/common.ts
export type ID = string;

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ListParams {
  page?: number;
  pageSize?: number;
  q?: string;
  sort?: string;
}

export interface ResultOK<T> { ok: true; data: T; }
export interface ResultErr  { ok: false; error: { status?: number; message: string; details?: unknown } }
export type Result<T> = ResultOK<T> | ResultErr;

export function ok<T>(data: T): Result<T> { return { ok: true, data }; }
export function err(message: string, status?: number, details?: unknown): Result<never> {
  const errorPayload: ResultErr["error"] = { message };
  if (typeof status === "number") {
    errorPayload.status = status;
  }
  if (details !== undefined) {
    errorPayload.details = details;
  }
  return { ok: false, error: errorPayload };
}

// Type guards (suaves) para protección mínima en runtime
export function isArray<T = unknown>(v: unknown): v is T[] { return Array.isArray(v); }
export function isObject(v: unknown): v is Record<string, unknown> { return v !== null && typeof v === "object" && !Array.isArray(v); }
