// [PACK25-OFFLINE-SVC-START]
type QueueItem = { type: "customer:create"|"customer:update"|"quote:create"|"return:create"; payload: any };
const KEY = "sm_offline_queue";

export function enqueue(item: QueueItem){
  try {
    const q: QueueItem[] = JSON.parse(localStorage.getItem(KEY) || "[]");
    q.push(item);
    localStorage.setItem(KEY, JSON.stringify(q));
    return true;
  } catch { return false; }
}

export function readQueue(): QueueItem[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}

export function replaceQueue(items: QueueItem[]){
  localStorage.setItem(KEY, JSON.stringify(items));
}
// [PACK25-OFFLINE-SVC-END]
