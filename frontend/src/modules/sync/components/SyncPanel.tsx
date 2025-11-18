import { useState } from "react";

type Props = {
  onSync: () => Promise<void> | void;
  onBackup: () => Promise<void> | void;
  onDownloadPdf: () => Promise<void> | void;
  onExportCsv: () => Promise<void> | void;
  syncStatus: string | null;
  conflictCount?: number;
  lastConflictAt?: Date | null;
  onResolveConflicts?: () => Promise<void> | void;
};

function SyncPanel({
  onSync,
  onBackup,
  onDownloadPdf,
  onExportCsv,
  onResolveConflicts,
  syncStatus,
  conflictCount = 0,
  lastConflictAt,
}: Props) {
  const [processing, setProcessing] = useState(false);

  const handleAction = async (action: () => Promise<void> | void) => {
    try {
      setProcessing(true);
      await action();
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="sync-panel">
      <div className="actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={processing}
          onClick={() => handleAction(onSync)}
        >
          Sincronizar ahora
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          disabled={processing}
          onClick={() => handleAction(onExportCsv)}
        >
          Exportar CSV
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          disabled={processing}
          onClick={() => handleAction(onDownloadPdf)}
        >
          Descargar PDF
        </button>
        <button
          type="button"
          className="btn btn--secondary"
          disabled={processing}
          onClick={() => handleAction(onBackup)}
        >
          Generar respaldo
        </button>
      </div>
      {processing ? <p className="processing">Procesando…</p> : null}
      {syncStatus ? <span className="pill accent">{syncStatus}</span> : null}
      {conflictCount > 0 ? (
        <div className="sync-panel__alert" role="status" aria-live="polite">
          <div>
            <p className="sync-panel__alert-title">
              Conflictos detectados en la cola híbrida ({conflictCount})
            </p>
            <p className="sync-panel__alert-subtitle">
              La estrategia last-write-wins priorizará el último envío, pero puedes resolverlos manualmente.
            </p>
            {lastConflictAt ? (
              <p className="sync-panel__alert-subtitle">Último conflicto: {lastConflictAt.toLocaleString("es-MX")}</p>
            ) : null}
          </div>
          {onResolveConflicts ? (
            <button
              type="button"
              className="btn btn-warning"
              disabled={processing}
              onClick={() => handleAction(onResolveConflicts)}
            >
              Resolver conflictos
            </button>
          ) : null}
        </div>
      ) : (
        <p className="sync-panel__hint">Sin conflictos pendientes en sync_outbox.</p>
      )}
    </div>
  );
}

export default SyncPanel;
