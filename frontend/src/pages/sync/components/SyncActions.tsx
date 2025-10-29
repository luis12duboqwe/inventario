import SyncPanel from "../../../modules/sync/components/SyncPanel";
import type { SyncBackupEntry } from "../../../types/sync";

type SyncActionsProps = {
  onSync: () => void | Promise<void>;
  syncStatus: string | null;
  onDownloadPdf: () => void;
  onBackup: () => void | Promise<void>;
  onExportCsv: () => void;
  backupHistory: SyncBackupEntry[];
  formatDateTime: (value?: string | null) => string;
};

function SyncActions({
  onSync,
  syncStatus,
  onDownloadPdf,
  onBackup,
  onExportCsv,
  backupHistory,
  formatDateTime,
}: SyncActionsProps) {
  return (
    <section className="card">
      <h2>Sincronización y reportes</h2>
      <SyncPanel
        onSync={onSync}
        syncStatus={syncStatus}
        onDownloadPdf={onDownloadPdf}
        onBackup={onBackup}
        onExportCsv={onExportCsv}
      />
      <div className="section-divider">
        <h3>Historial de respaldos</h3>
        {backupHistory.length === 0 ? (
          <p className="muted-text">No existen respaldos previos.</p>
        ) : (
          <ul className="history-list">
            {backupHistory.map((backup) => (
              <li key={backup.id}>
                <span className="badge neutral">{backup.mode}</span>
                <span>{formatDateTime(backup.executed_at)}</span>
                <span>{(backup.total_size_bytes / 1024).toFixed(1)} KB</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export type { SyncActionsProps };
export default SyncActions;
