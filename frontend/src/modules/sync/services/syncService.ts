import {
  runBackup,
  triggerSync,
  listSyncOutbox,
  retrySyncOutbox,
  getSyncOutboxStats,
  getSyncHistory,
  enqueueSyncQueueEvents,
  dispatchSyncQueueEvents,
  listSyncQueueStatus,
  resolveSyncQueueEvent,
} from "../../../api";

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
