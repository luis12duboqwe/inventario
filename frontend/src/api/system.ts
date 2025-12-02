import { request, requestCollection } from "./client";

export type BackupJob = {
  id: number;
  mode: "automatico" | "manual";
  executed_at: string;
  pdf_path: string;
  archive_path: string;
  total_size_bytes: number;
  notes?: string | null;
};

export type ReleaseInfo = {
  version: string;
  release_date: string;
  notes: string;
  download_url: string;
};

export type UpdateStatus = {
  current_version: string;
  latest_version: string | null;
  is_update_available: boolean;
  latest_release: ReleaseInfo | null;
};

export function runBackup(token: string, reason: string, note?: string): Promise<BackupJob> {
  return request<BackupJob>("/backups/run", {
    method: "POST",
    body: JSON.stringify({ nota: note }),
    headers: {
      "X-Reason": reason,
    },
  }, token);
}

export function fetchBackupHistory(token: string): Promise<BackupJob[]> {
  return requestCollection<BackupJob>("/backups/history", { method: "GET" }, token);
}

export function getUpdateStatus(token: string): Promise<UpdateStatus> {
  return request<UpdateStatus>("/updates/status", { method: "GET" }, token);
}

export function getReleaseHistory(token: string, limit = 10): Promise<ReleaseInfo[]> {
  return requestCollection<ReleaseInfo>(`/updates/history?limit=${limit}`, { method: "GET" }, token);
}
