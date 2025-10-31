// src/services/http.ts
// Ligero wrapper sobre fetch con baseURL, timeout, auth opcional y manejo uniforme de errores.

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface HttpOptions {
  method?: HttpMethod;
  headers?: Record<string, string>;
  query?: Record<string, any>;
  body?: any;
  withAuth?: boolean;
  signal?: AbortSignal;
  timeoutMs?: number;
  // [PACK25-HTTP-OPTS-EXT-START]
  cacheTtlMs?: number;
  cacheKey?: string;
  // [PACK25-HTTP-OPTS-EXT-END]
}

export interface ApiError {
  status: number;
  message: string;
  details?: any;
}

const BASE = (import.meta as any)?.env?.VITE_API_BASE_URL || "";
const DEFAULT_TIMEOUT = Number((import.meta as any)?.env?.VITE_API_TIMEOUT_MS ?? 18000);
// [PACK25-HTTP-CACHE-START]
const __memCache = new Map<string, { at:number; data:any; ttl:number }>();
function readCache(key:string){ const v = __memCache.get(key); if(!v) return null; if(Date.now()-v.at > v.ttl) { __memCache.delete(key); return null; } return v.data; }
function writeCache(key:string, data:any, ttl:number){ __memCache.set(key, { at: Date.now(), data, ttl }); }
// [PACK25-HTTP-CACHE-END]

function toQuery(q?: Record<string, any>) {
  if (!q) return "";
  const p = Object.entries(q)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return p ? `?${p}` : "";
}

function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  if (!ms) return p;
  let t: any;
  return new Promise((resolve, reject) => {
    t = setTimeout(() => reject(new Error("Request timeout")), ms);
    p.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
  });
}

export async function http<T>(path: string, opts: HttpOptions = {}): Promise<T> {
  const url = `${BASE}${path}${toQuery(opts.query)}`;
  // [PACK25-HTTP-READCACHE-START]
  const cacheKey = opts.cacheKey || (opts.method === "GET" || !opts.method ? url : undefined);
  if (opts.cacheTtlMs && cacheKey){
    const hit = readCache(cacheKey);
    if (hit) return hit as T;
  }
  // [PACK25-HTTP-READCACHE-END]
  const headers: Record<string, string> = {
    "Accept": "application/json",
    ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
    ...(opts.headers || {}),
  };

  if (opts.withAuth) {
    const token = localStorage.getItem("access_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const init: RequestInit = {
    method: opts.method || "GET",
    headers,
    body: opts.body && !(opts.body instanceof FormData) ? JSON.stringify(opts.body) : opts.body,
    signal: opts.signal,
  };

  const doFetch = async () => {
    const res = await fetch(url, init);
    const isJson = res.headers.get("content-type")?.includes("application/json");
    if (!res.ok) {
      let message = `HTTP ${res.status}`;
      let details: any;
      if (isJson) {
        try { const j = await res.json(); message = j?.detail ?? j?.message ?? message; details = j; } catch {}
      } else {
        try { message = await res.text(); } catch {}
      }
      const err: ApiError = { status: res.status, message, details };
      throw err;
    }
    let payload: any;
    if (!isJson) {
      payload = await res.text();
    } else {
      payload = await res.json();
    }
    // [PACK25-HTTP-WRITECACHE-START]
    if (opts.cacheTtlMs && cacheKey){
      writeCache(cacheKey, payload, opts.cacheTtlMs);
    }
    // [PACK25-HTTP-WRITECACHE-END]
    return payload as T;
  };

  return withTimeout(doFetch(), opts.timeoutMs ?? DEFAULT_TIMEOUT);
}

export const httpGet  = <T>(path: string, opts: HttpOptions = {}) => http<T>(path, { ...opts, method: "GET" });
export const httpPost = <T>(path: string, body?: any, opts: HttpOptions = {}) => http<T>(path, { ...opts, method: "POST", body });
export const httpPut  = <T>(path: string, body?: any, opts: HttpOptions = {}) => http<T>(path, { ...opts, method: "PUT", body });
export const httpDel  = <T>(path: string, opts: HttpOptions = {}) => http<T>(path, { ...opts, method: "DELETE" });
