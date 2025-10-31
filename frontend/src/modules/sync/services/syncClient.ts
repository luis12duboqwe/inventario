// [PACK35-frontend]
import { enqueueSyncQueueEvents } from "../../../api";

export type LocalSyncQueueStatus = "pending" | "sending" | "sent" | "failed";

export type LocalSyncEventInput = {
  eventType: string;
  payload: Record<string, unknown>;
  idempotencyKey?: string;
};

export type LocalSyncQueueItem = {
  id: number;
  eventType: string;
  payload: Record<string, unknown>;
  status: LocalSyncQueueStatus;
  attempts: number;
  lastError: string | null;
  idempotencyKey?: string | null;
  remoteId?: number | null;
  createdAt: number;
  updatedAt: number;
  nextAttemptAt: number | null;
};

type FlushSummary = {
  sent: number;
  failed: number;
  retried: number;
};

const DB_NAME = "softmobile_sync_pack35";
const STORE_NAME = "queue";
const DB_VERSION = 1;
const MAX_HISTORY = 200;

const listeners = new Set<() => void>();
let authToken: string | null = null;
let autoFlushHandle: number | null = null;

type StorageDriver = {
  add(item: LocalSyncQueueItem): Promise<LocalSyncQueueItem>;
  update(id: number, updates: Partial<LocalSyncQueueItem>): Promise<LocalSyncQueueItem | null>;
  all(): Promise<LocalSyncQueueItem[]>;
  remove(ids: number[]): Promise<void>;
};

const memoryStore: LocalSyncQueueItem[] = [];

function now(): number {
  return Date.now();
}

function retryDelay(attempt: number): number {
  const base = 4000;
  const exponent = Math.min(attempt, 6);
  return Math.min(base * 2 ** exponent, 5 * 60 * 1000);
}

async function openDatabase(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") {
    throw new Error("IndexedDB no soportado");
  }
  return await new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
        store.createIndex("status", "status", { unique: false });
        store.createIndex("updatedAt", "updatedAt", { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("No fue posible abrir IndexedDB"));
  });
}

const indexedDbDriver: StorageDriver = {
  async add(item) {
    const db = await openDatabase();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const request = store.add(item);
      request.onsuccess = () => {
        const id = Number(request.result);
        resolve({ ...item, id });
      };
      request.onerror = () => reject(request.error ?? new Error("No fue posible guardar el evento"));
    });
  },
  async update(id, updates) {
    const db = await openDatabase();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const getRequest = store.get(id);
      getRequest.onsuccess = () => {
        const current = getRequest.result as LocalSyncQueueItem | undefined;
        if (!current) {
          resolve(null);
          return;
        }
        const next: LocalSyncQueueItem = { ...current, ...updates };
        const putRequest = store.put(next);
        putRequest.onsuccess = () => resolve(next);
        putRequest.onerror = () => reject(putRequest.error ?? new Error("No fue posible actualizar el evento"));
      };
      getRequest.onerror = () => reject(getRequest.error ?? new Error("No fue posible leer el evento"));
    });
  },
  async all() {
    const db = await openDatabase();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const request = store.getAll();
      request.onsuccess = () => resolve((request.result as LocalSyncQueueItem[]) ?? []);
      request.onerror = () => reject(request.error ?? new Error("No fue posible leer la cola local"));
    });
  },
  async remove(ids) {
    const db = await openDatabase();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      ids.forEach((id) => store.delete(id));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error ?? new Error("No fue posible depurar la cola"));
    });
  },
};

const memoryDriver: StorageDriver = {
  async add(item) {
    const id = item.id ?? memoryStore.length + 1;
    const record = { ...item, id };
    memoryStore.push(record);
    return record;
  },
  async update(id, updates) {
    const index = memoryStore.findIndex((item) => item.id === id);
    if (index === -1) {
      return null;
    }
    memoryStore[index] = { ...memoryStore[index], ...updates };
    return memoryStore[index];
  },
  async all() {
    return [...memoryStore];
  },
  async remove(ids) {
    ids.forEach((target) => {
      const index = memoryStore.findIndex((item) => item.id === target);
      if (index >= 0) {
        memoryStore.splice(index, 1);
      }
    });
  },
};

function getDriver(): StorageDriver {
  if (typeof window === "undefined" || typeof indexedDB === "undefined") {
    return memoryDriver;
  }
  return indexedDbDriver;
}

async function pruneHistory(driver: StorageDriver): Promise<void> {
  const records = await driver.all();
  const sent = records.filter((item) => item.status === "sent");
  if (sent.length <= MAX_HISTORY) {
    return;
  }
  const sorted = sent.sort((a, b) => a.updatedAt - b.updatedAt);
  const excess = sorted.slice(0, sent.length - MAX_HISTORY);
  await driver.remove(excess.map((item) => item.id));
}

async function readSnapshot(driver: StorageDriver): Promise<LocalSyncQueueItem[]> {
  const records = await driver.all();
  return records.sort((a, b) => b.createdAt - a.createdAt);
}

async function notifyListeners(): Promise<void> {
  await pruneHistory(getDriver());
  listeners.forEach((listener) => listener());
}

async function flushInternal(): Promise<FlushSummary> {
  const driver = getDriver();
  const entries = await driver.all();
  const ready = entries
    .filter((item) => ["pending", "failed"].includes(item.status))
    .filter((item) => item.nextAttemptAt == null || item.nextAttemptAt <= now());

  if (ready.length === 0 || !authToken || typeof navigator !== "undefined" && !navigator.onLine) {
    return { sent: 0, failed: 0, retried: 0 };
  }

  await Promise.all(
    ready.map((item) =>
      driver.update(item.id, {
        status: "sending",
        updatedAt: now(),
      })
    )
  );

  const events = ready.map((item) => ({
    event_type: item.eventType,
    payload: item.payload,
    idempotency_key: item.idempotencyKey ?? undefined,
  }));

  try {
    const response = await enqueueSyncQueueEvents(authToken, events);
    const remoteByKey = new Map<string, number>();
    [...response.queued, ...response.reused].forEach((entry) => {
      if (entry.idempotency_key) {
        remoteByKey.set(entry.idempotency_key, entry.id);
      }
    });
    const orderedRemote = [...response.queued, ...response.reused];

    await Promise.all(
      ready.map((item, index) => {
        const remoteIdFromKey = item.idempotencyKey ? remoteByKey.get(item.idempotencyKey) : undefined;
        const remoteId = remoteIdFromKey ?? orderedRemote[index]?.id ?? null;
        return driver.update(item.id, {
          status: "sent",
          lastError: null,
          attempts: item.attempts + 1,
          remoteId,
          updatedAt: now(),
          nextAttemptAt: null,
        });
      })
    );
    await notifyListeners();
    return { sent: ready.length, failed: 0, retried: 0 };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Error al enviar eventos";
    await Promise.all(
      ready.map((item) =>
        driver.update(item.id, {
          status: "failed",
          lastError: message,
          attempts: item.attempts + 1,
          updatedAt: now(),
          nextAttemptAt: now() + retryDelay(item.attempts + 1),
        })
      )
    );
    await notifyListeners();
    return { sent: 0, failed: ready.length, retried: ready.length };
  }
}

function scheduleAutoFlush(): void {
  if (typeof window === "undefined") {
    return;
  }
  if (autoFlushHandle !== null) {
    return;
  }
  autoFlushHandle = window.setInterval(() => {
    void flushInternal();
  }, 15000);
}

function cancelAutoFlush(): void {
  if (typeof window === "undefined") {
    return;
  }
  if (autoFlushHandle !== null) {
    window.clearInterval(autoFlushHandle);
    autoFlushHandle = null;
  }
}

async function enqueue(event: LocalSyncEventInput): Promise<LocalSyncQueueItem> {
  const driver = getDriver();
  const timestamp = now();
  const record: LocalSyncQueueItem = {
    id: 0,
    eventType: event.eventType,
    payload: event.payload,
    status: "pending",
    attempts: 0,
    lastError: null,
    idempotencyKey: event.idempotencyKey ?? null,
    remoteId: null,
    createdAt: timestamp,
    updatedAt: timestamp,
    nextAttemptAt: null,
  };
  const saved = await driver.add(record);
  await notifyListeners();
  return saved;
}

async function snapshot(): Promise<{ pending: LocalSyncQueueItem[]; history: LocalSyncQueueItem[] }> {
  const driver = getDriver();
  const data = await readSnapshot(driver);
  return {
    pending: data.filter((item) => item.status !== "sent"),
    history: data,
  };
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function setToken(token: string | null): void {
  authToken = token;
  if (token) {
    scheduleAutoFlush();
  } else {
    cancelAutoFlush();
  }
}

function init(): void {
  if (typeof window === "undefined") {
    return;
  }
  if (typeof indexedDB !== "undefined") {
    void openDatabase().catch(() => {
      /* IndexedDB podría no estar disponible en modo privado */
    });
  }
  window.addEventListener("online", () => {
    void flushInternal();
  });
}

export const syncClient = {
  init,
  enqueue, // [PACK35-frontend]
  snapshot,
  subscribe,
  setToken,
  flush: flushInternal,
};

export type SyncClientFlushSummary = FlushSummary;
