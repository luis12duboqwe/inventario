import { runBackup } from "@api/system";
import {
  triggerSync,
  listSyncOutbox,
  retrySyncOutbox,
  getSyncOutboxStats,
  getSyncHistory,
  enqueueSyncQueueEvents,
  dispatchSyncQueueEvents,
  listSyncQueueStatus,
  resolveSyncQueueEvent,
} from "@api/sync";

export const syncService = {
  runBackup,
  triggerSync,
  listSyncOutbox,
  retrySyncOutbox,
  getSyncOutboxStats,
  getSyncHistory,
  enqueueSyncQueueEvents, // [PACK35-frontend]
  dispatchSyncQueueEvents,
  listSyncQueueStatus,
  resolveSyncQueueEvent,
};
