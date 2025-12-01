// [PACK35-frontend]
import { useCallback, useEffect, useState } from "react";

import type { SyncClientFlushSummary } from "../services/syncClient";
import { syncClient, type LocalSyncEventInput, type LocalSyncQueueItem } from "../services/syncClient";

type UseSyncQueueResult = {
  pending: LocalSyncQueueItem[];
  history: LocalSyncQueueItem[];
  loading: boolean;
  online: boolean;
  lastSummary: SyncClientFlushSummary | null;
  progress: {
    percent: number;
    total: number;
    sent: number;
    pending: number;
    failed: number;
  };
  enqueueDemo: () => Promise<LocalSyncQueueItem>;
  flush: () => Promise<SyncClientFlushSummary>;
  resetSummary: () => void;
};

const demoEvent: LocalSyncEventInput = {
  eventType: "demo.event",
  payload: { motivo: "Generado desde panel" },
};

export function useSyncQueue(token: string | null): UseSyncQueueResult {
  const [pending, setPending] = useState<LocalSyncQueueItem[]>([]);
  const [history, setHistory] = useState<LocalSyncQueueItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastSummary, setLastSummary] = useState<SyncClientFlushSummary | null>(null);
  const [progress, setProgress] = useState<UseSyncQueueResult["progress"]>({
    percent: 100,
    total: 0,
    sent: 0,
    pending: 0,
    failed: 0,
  });
  const [online, setOnline] = useState<boolean>(() => {
    if (typeof navigator === "undefined") {
      return true;
    }
    return navigator.onLine;
  });

  const refresh = useCallback(async () => {
    setLoading(true);
    const snapshot = await syncClient.snapshot();
    setPending(snapshot.pending);
    setHistory(snapshot.history);
    const total = snapshot.history.length;
    const sent = snapshot.history.filter((item) => item.status === "sent").length;
    const failed = snapshot.history.filter((item) => item.status === "failed").length;
    const pendingCount = snapshot.pending.filter((item) => item.status !== "failed").length;
    const percent = total === 0 ? 100 : Math.round((sent / total) * 100);
    setProgress({
      percent: Math.max(0, Math.min(100, percent)),
      total,
      sent,
      pending: pendingCount,
      failed,
    });
    setLoading(false);
  }, []);

  useEffect(() => {
    syncClient.init();
    const unsubscribe = syncClient.subscribe(() => {
      void refresh();
    });
    // Evitar setState sincrónico en el cuerpo del efecto
    Promise.resolve().then(() => {
      void refresh();
    });
    return unsubscribe;
  }, [refresh]);

  useEffect(() => {
    syncClient.setToken(token);
  }, [token]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const update = () => {
      setOnline(typeof navigator === "undefined" ? true : navigator.onLine);
    };
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const flush = useCallback(async () => {
    const summary = await syncClient.flush();
    setLastSummary(summary);
    await refresh();
    return summary;
  }, [refresh]);

  const enqueueDemo = useCallback(async () => {
    const event = await syncClient.enqueue({
      ...demoEvent,
      payload: { ...demoEvent.payload, generado_en: new Date().toISOString() },
    });
    await refresh();
    return event;
  }, [refresh]);

  const resetSummary = useCallback(() => setLastSummary(null), []);

  return {
    pending,
    history,
    loading,
    online,
    lastSummary,
    progress,
    enqueueDemo,
    flush,
    resetSummary,
  };
}
