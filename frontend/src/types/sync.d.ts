import type { ModuleStatus } from "../shared/components/ModuleHeader";

type RecentSyncLog = {
  id: string;
  storeName: string;
  status: string;
  mode: string;
  startedAt: string;
  finishedAt: string | null;
  errorMessage: string | null;
};

type SyncBackupEntry = {
  id: string;
  mode: string;
  executed_at: string;
  total_size_bytes: number;
};

type SyncSummaryMetric = {
  label: string;
  value: string | number;
  description: string;
};

export type { ModuleStatus, RecentSyncLog, SyncBackupEntry, SyncSummaryMetric };
