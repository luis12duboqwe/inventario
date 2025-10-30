// [PACK25-OFFLINE-WIRE-START]
import { enqueue, readQueue, replaceQueue } from "@/services/offline";
import type { ApiError } from "@/services/http";
import { SalesCustomers, SalesQuotes, SalesReturns } from "@/services/sales";

export type OfflineActionResult<T> =
  | { status: "ok"; data: T }
  | { status: "queued" }
  | { status: "error"; error: unknown };

function shouldEnqueue(error: unknown): boolean {
  const apiError = error as ApiError | undefined;
  if (apiError && typeof apiError.status === "number") {
    if (apiError.status >= 400 && apiError.status < 500) {
      return false;
    }
    if (apiError.status >= 500) {
      return false;
    }
  }
  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    if (message.includes("timeout") || message.includes("network")) {
      return true;
    }
  }
  if (error && typeof (error as { name?: string }).name === "string") {
    const name = (error as { name?: string }).name?.toLowerCase();
    if (name === "aborterror") {
      return true;
    }
  }
  return !(apiError && typeof apiError.status === "number");
}

async function executeWithOfflineFallback<T>(
  action: () => Promise<T>,
  queueItem: () => void,
): Promise<OfflineActionResult<T>> {
  try {
    const data = await action();
    return { status: "ok", data };
  } catch (error) {
    if (shouldEnqueue(error)) {
      queueItem();
      return { status: "queued" };
    }
    return { status: "error", error };
  }
}

export async function safeCreateCustomer(dto:any): Promise<OfflineActionResult<any>>{
  return executeWithOfflineFallback(
    () => SalesCustomers.createCustomer(dto),
    () => enqueue({ type:"customer:create", payload:dto }),
  );
}

export async function safeUpdateCustomer(id:string, dto:any): Promise<OfflineActionResult<any>>{
  return executeWithOfflineFallback(
    () => SalesCustomers.updateCustomer(id, dto),
    () => enqueue({ type:"customer:update", payload:{ id, dto } }),
  );
}

export async function safeCreateQuote(dto:any): Promise<OfflineActionResult<any>>{
  return executeWithOfflineFallback(
    () => SalesQuotes.createQuote(dto),
    () => enqueue({ type:"quote:create", payload:dto }),
  );
}

export async function safeCreateReturn(dto:any): Promise<OfflineActionResult<any>>{
  return executeWithOfflineFallback(
    () => SalesReturns.createReturn(dto),
    () => enqueue({ type:"return:create", payload:dto }),
  );
}

export async function flushOffline(){
  const q = readQueue(); const next: typeof q = [];
  for (const item of q){
    try {
      if (item.type === "customer:create") await SalesCustomers.createCustomer(item.payload);
      else if (item.type === "customer:update") await SalesCustomers.updateCustomer(item.payload.id, item.payload.dto);
      else if (item.type === "quote:create") await SalesQuotes.createQuote(item.payload);
      else if (item.type === "return:create") await SalesReturns.createReturn(item.payload);
    } catch { next.push(item); }
  }
  replaceQueue(next);
  return { flushed: q.length - next.length, pending: next.length };
}
// [PACK25-OFFLINE-WIRE-END]
