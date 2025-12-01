import { useState, useCallback } from "react";
import {
  fetchBackupHistory,
  getReleaseHistory,
  getUpdateStatus,
  runBackup,
} from "@api/system";
import { getCurrentUser } from "@api/users";
import { safeArray } from "../../../utils/safeValues";
import type { BackupJob, ReleaseInfo, UpdateStatus } from "@api/system";
import type { UserAccount } from "@api/users";
import type { ToastMessage } from "../hooks/useUIState";

export function useSystemData(token: string, pushToast: (toast: Omit<ToastMessage, "id">) => void, friendlyErrorMessage: (msg: string) => string) {
  const [backupHistory, setBackupHistory] = useState<BackupJob[]>([]);
  const [releaseHistory, setReleaseHistory] = useState<ReleaseInfo[]>([]);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const [currentUser, setCurrentUser] = useState<UserAccount | null>(null);

  const fetchSystemData = useCallback(async () => {
    try {
      const [backupRaw, statusData, releasesRaw] = await Promise.all([
        fetchBackupHistory(token),
        getUpdateStatus(token),
        getReleaseHistory(token),
      ]);
      setBackupHistory(safeArray(backupRaw));
      setUpdateStatus(statusData);
      setReleaseHistory(safeArray(releasesRaw));

      try {
        const userData = await getCurrentUser(token);
        setCurrentUser(userData);
      } catch (userErr) {
        const message = userErr instanceof Error ? userErr.message : "No fue posible obtener el usuario actual";
        setCurrentUser(null);
        pushToast({ message, variant: "error" });
      }
    } catch (err) {
      console.error("Error fetching system data", err);
    }
  }, [token, pushToast]);

  const handleBackup = useCallback(
    async (reason: string, note?: string, setError?: (msg: string | null) => void, setMessage?: (msg: string | null) => void) => {
      const normalizedReason = reason.trim();
      if (normalizedReason.length < 5) {
        const message = "Indica un motivo corporativo de al menos 5 caracteres.";
        if (setError) setError(message);
        pushToast({ message, variant: "error" });
        return;
      }

      const resolvedNote = (note ?? "Respaldo manual desde tienda").trim() || "Respaldo manual desde tienda";

      try {
        if (setError) setError(null);
        const job = await runBackup(token, normalizedReason, resolvedNote);
        setBackupHistory((current) => [job, ...current].slice(0, 10));
        if (setMessage) setMessage("Respaldo generado y almacenado en el servidor central");
        pushToast({ message: "Respaldo generado", variant: "success" });
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo generar el respaldo";
        const friendly = friendlyErrorMessage(message);
        if (setError) setError(friendly);
        pushToast({ message: friendly, variant: "error" });
      }
    },
    [token, pushToast, friendlyErrorMessage]
  );

  return {
    backupHistory,
    releaseHistory,
    updateStatus,
    currentUser,
    fetchSystemData,
    handleBackup,
  };
}
