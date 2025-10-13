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
    <div>
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
      {syncStatus ? <p style={{ marginTop: 12 }}>{syncStatus}</p> : null}
    </div>
  );
}

export default SyncPanel;
