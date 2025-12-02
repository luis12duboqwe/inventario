import { AxiosRequestConfig } from "axios";
import {
  httpClient,
  getCurrentApiBaseUrl,
  NETWORK_EVENT,
  NETWORK_RECOVERY_EVENT,
  UNAUTHORIZED_EVENT,
  parseFilenameFromDisposition,
} from "./http";
import { applyReasonHeader } from "../http/reasonInterceptor";
import { PaginatedResponse } from "./types";

export {
  NETWORK_EVENT,
  NETWORK_RECOVERY_EVENT,
  UNAUTHORIZED_EVENT,
  parseFilenameFromDisposition,
};

export const API_URL = getCurrentApiBaseUrl();

export function clearRequestCache(): void {
  // No-op: Cache is now handled by React Query or Axios (if configured)
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {};

  if (options.headers) {
    if (options.headers instanceof Headers) {
      options.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(options.headers)) {
      options.headers.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, options.headers);
    }
  }

  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!headers["Content-Type"] && !isFormData) {
    headers["Content-Type"] = "application/json";
  }
  if (isFormData) {
    delete headers["Content-Type"];
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const method = (options.method ?? "GET").toUpperCase();

  const headersInstance = new Headers(headers);
  applyReasonHeader(path, method, headersInstance);

  const finalHeaders: Record<string, string> = {};
  headersInstance.forEach((value, key) => {
    finalHeaders[key] = value;
  });

  const config: AxiosRequestConfig = {
    url: path,
    method: method,
    headers: finalHeaders,
    data: options.body,
    signal: options.signal as AbortSignal,
  };

  if (finalHeaders["Accept"] === "application/pdf" ||
      finalHeaders["Accept"] === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
      finalHeaders["Accept"] === "text/csv" ||
      path.includes("/export") ||
      path.includes("/pdf") ||
      path.includes("/csv") ||
      path.includes("/xlsx") ||
      path.includes("/label/")
     ) {
      config.responseType = 'blob';
  }

  const response = await httpClient.request(config);
  return response.data;
}

export function extractCollectionItems<T>(payload: PaginatedResponse<T> | T[]): T[] {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.items)) {
    return payload.items;
  }
  return [];
}

export function requestCollection<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T[]> {
  return request<PaginatedResponse<T> | T[]>(path, options, token).then((payload) =>
    extractCollectionItems(payload)
  );
}
