// [PACK25-OFFLINE-WIRE-START]
import { enqueue, readQueue, removeItems, type QueueItem } from "@/services/offline";
import { SalesCustomers, SalesQuotes, SalesReturns } from "@/services/sales";
import type { Customer, QuoteCreate, ReturnCreate } from "@/services/sales/types";

type CustomerCreate = Omit<Customer, "id">;
type CustomerUpdate = Partial<Omit<Customer, "id">>;

export async function safeCreateCustomer(dto: CustomerCreate) {
  try {
    return await SalesCustomers.createCustomer(dto);
  } catch {
    enqueue({ type: "customer:create", payload: dto });
    return null;
  }
}

export async function safeUpdateCustomer(id: string, dto: CustomerUpdate) {
  try {
    return await SalesCustomers.updateCustomer(id, dto);
  } catch {
    enqueue({ type: "customer:update", payload: { id, dto } });
    return null;
  }
}

export async function safeCreateQuote(dto: QuoteCreate) {
  try {
    return await SalesQuotes.createQuote(dto);
  } catch {
    enqueue({ type: "quote:create", payload: dto });
    return null;
  }
}

export async function safeCreateReturn(dto: ReturnCreate) {
  try {
    return await SalesReturns.createReturn(dto);
  } catch {
    enqueue({ type: "return:create", payload: dto });
    return null;
  }
}

// Type guards to avoid casting
function isCustomerCreate(item: QueueItem): item is QueueItem & { type: "customer:create"; payload: CustomerCreate } {
  return item.type === "customer:create";
}

function isCustomerUpdate(item: QueueItem): item is QueueItem & { type: "customer:update"; payload: { id: string; dto: CustomerUpdate } } {
  return item.type === "customer:update";
}

function isQuoteCreate(item: QueueItem): item is QueueItem & { type: "quote:create"; payload: QuoteCreate } {
  return item.type === "quote:create";
}

function isReturnCreate(item: QueueItem): item is QueueItem & { type: "return:create"; payload: ReturnCreate } {
  return item.type === "return:create";
}

let isFlushing = false;

export async function flushOffline() {
  if (isFlushing) return { flushed: 0, pending: 0 };
  isFlushing = true;

  try {
    const q = readQueue();
    const processedIds: string[] = [];
    let successCount = 0;
    let failCount = 0;

    for (const item of q) {
      try {
        if (isCustomerCreate(item)) {
          await SalesCustomers.createCustomer(item.payload);
        } else if (isCustomerUpdate(item)) {
          await SalesCustomers.updateCustomer(item.payload.id, item.payload.dto);
        } else if (isQuoteCreate(item)) {
          await SalesQuotes.createQuote(item.payload);
        } else if (isReturnCreate(item)) {
          await SalesReturns.createReturn(item.payload);
        }
        processedIds.push(item.id);
        successCount++;
      } catch {
        failCount++;
      }
    }

    if (processedIds.length > 0) {
      removeItems(processedIds);
    }

    return { flushed: successCount, pending: failCount };
  } finally {
    isFlushing = false;
  }
}
// [PACK25-OFFLINE-WIRE-END]
