import { useState } from "react";

type Props = {
  onSync: () => Promise<void> | void;
  onBackup: () => Promise<void> | void;
  onDownloadPdf: () => Promise<void> | void;
  syncStatus: string | null;
};

function SyncPanel({ onSync, onBackup, onDownloadPdf, syncStatus }: Props) {
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
        <button type="button" disabled={processing} onClick={() => handleAction(onSync)}>
          Sincronizar ahora
        </button>
        <button type="button" className="secondary" disabled={processing} onClick={() => handleAction(onDownloadPdf)}>
          Descargar PDF
        </button>
        <button type="button" disabled={processing} onClick={() => handleAction(onBackup)}>
          Generar respaldo
        </button>
      </div>
      {processing ? <p className="processing">Procesando…</p> : null}
      {syncStatus ? <span className="pill accent">{syncStatus}</span> : null}
    </div>
  );
}

export default SyncPanel;
