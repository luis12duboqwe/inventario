import SyncPanel from "../SyncPanel";
import { useDashboard } from "./DashboardContext";

function SyncSection() {
  const {
    handleSync,
    handleBackup,
    downloadInventoryReport,
    syncStatus,
    backupHistory,
    releaseHistory,
    updateStatus,
    enableHybridPrep,
    outbox,
    outboxError,
    refreshOutbox,
    handleRetryOutbox,
  } = useDashboard();

  const latestRelease = updateStatus?.latest_release ?? null;

  return (
    <div className="section-grid">
      <section className="card">
        <h2>Sincronización y reportes</h2>
        <SyncPanel
          onSync={handleSync}
          syncStatus={syncStatus}
          onDownloadPdf={downloadInventoryReport}
          onBackup={handleBackup}
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
                  <span>{new Date(backup.executed_at).toLocaleString("es-MX")}</span>
                  <span>{(backup.total_size_bytes / 1024).toFixed(1)} KB</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="card">
        <h2>Historial de versiones</h2>
        {latestRelease ? (
          <p>
            Última liberación corporativa:
            <strong> {latestRelease.version}</strong> · {new Date(latestRelease.release_date).toLocaleDateString("es-MX")} ·
            <a className="accent-link" href={latestRelease.download_url} target="_blank" rel="noreferrer">
              Descargar instalador
            </a>
          </p>
        ) : (
          <p className="muted-text">No se han publicado versiones en el feed.</p>
        )}
        {releaseHistory.length > 0 ? (
          <ul className="history-list releases">
            {releaseHistory.map((release) => (
              <li key={release.version}>
                <strong>{release.version}</strong> · {new Date(release.release_date).toLocaleDateString("es-MX")} · {release.notes}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="card">
        <h2>Cola de sincronización local</h2>
        <p className="card-subtitle">Eventos pendientes de envío a la nube corporativa.</p>
        {enableHybridPrep ? (
          <>
            <div className="outbox-actions">
              <button className="btn" onClick={refreshOutbox} type="button">
                Actualizar estado
              </button>
              <button
                className="btn ghost"
                onClick={handleRetryOutbox}
                type="button"
                disabled={outbox.length === 0}
              >
                Reintentar pendientes
              </button>
            </div>
            {outboxError && <p className="error-text">{outboxError}</p>}
            {outbox.length === 0 ? (
              <p className="muted-text">Sin eventos en la cola local.</p>
            ) : (
              <table className="outbox-table">
                <thead>
                  <tr>
                    <th>Entidad</th>
                    <th>Operación</th>
                    <th>Intentos</th>
                    <th>Estado</th>
                    <th>Actualizado</th>
                  </tr>
                </thead>
                <tbody>
                  {outbox.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        {entry.entity_type} #{entry.entity_id}
                      </td>
                      <td>{entry.operation}</td>
                      <td>{entry.attempt_count}</td>
                      <td>{entry.status}</td>
                      <td>{new Date(entry.updated_at).toLocaleString("es-MX")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        ) : (
          <p className="muted-text">
            La sincronización híbrida está desactivada. Ajusta el flag <code>SOFTMOBILE_ENABLE_HYBRID_PREP</code> para habilitar
            la cola local.
          </p>
        )}
      </section>
    </div>
  );
}

export default SyncSection;

