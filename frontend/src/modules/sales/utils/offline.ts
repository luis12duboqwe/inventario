// [PACK25-OFFLINE-WIRE-START]
import { enqueue, readQueue, replaceQueue } from "@/services/offline";
import { SalesCustomers, SalesQuotes, SalesReturns } from "@/services/sales";

export async function safeCreateCustomer(dto:any){
  try { return await SalesCustomers.createCustomer(dto); }
  catch(e){ enqueue({ type:"customer:create", payload:dto }); return null; }
}

export async function safeUpdateCustomer(id:string, dto:any){
  try { return await SalesCustomers.updateCustomer(id, dto); }
  catch(e){ enqueue({ type:"customer:update", payload:{ id, dto } }); return null; }
}

export async function safeCreateQuote(dto:any){
  try { return await SalesQuotes.createQuote(dto); }
  catch(e){ enqueue({ type:"quote:create", payload:dto }); return null; }
}

export async function safeCreateReturn(dto:any){
  try { return await SalesReturns.createReturn(dto); }
  catch(e){ enqueue({ type:"return:create", payload:dto }); return null; }
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
