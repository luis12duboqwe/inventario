// [PACK25-OFFLINE-SVC-START]
export type QueueItem = {
  id: string;
  type: "customer:create" | "customer:update" | "quote:create" | "return:create";
  payload: unknown;
};

const KEY = "sm_offline_queue";

function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

export function enqueue(item: Omit<QueueItem, "id">) {
  try {
    const q: QueueItem[] = JSON.parse(localStorage.getItem(KEY) || "[]");
    q.push({ ...item, id: generateId() });
    localStorage.setItem(KEY, JSON.stringify(q));
    return true;
  } catch {
    return false;
  }
}

export function readQueue(): QueueItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function removeItems(idsToRemove: string[]) {
  try {
    const q: QueueItem[] = JSON.parse(localStorage.getItem(KEY) || "[]");
    const next = q.filter((item) => !idsToRemove.includes(item.id));
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export function replaceQueue(items: QueueItem[]) {
  localStorage.setItem(KEY, JSON.stringify(items));
}
// [PACK25-OFFLINE-SVC-END]
