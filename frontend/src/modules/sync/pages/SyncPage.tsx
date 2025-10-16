import { Repeat } from "lucide-react";

import SyncPanel from "../components/SyncPanel";
import ModuleHeader, { type ModuleStatus } from "../../../components/ModuleHeader";
import { useSyncModule } from "../hooks/useSyncModule";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { promptCorporateReason } from "../../../utils/corporateReason";

function SyncPage() {
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
    outboxStats,
    syncHistory,
    syncHistoryError,
    refreshSyncHistory,
  } = useSyncModule();
  const { pushToast, setError, selectedStore } = useDashboard();

  const latestRelease = updateStatus?.latest_release ?? null;

  const hasSyncFailure =
    typeof syncStatus === "string" && syncStatus.toLowerCase().includes("fall") ? true : false;
  let moduleStatus: ModuleStatus = "ok";
  let moduleStatusLabel = "Sincronización estable";

  if (outboxError || syncHistoryError || hasSyncFailure) {
    moduleStatus = "critical";
    moduleStatusLabel = "Atiende errores recientes de sincronización";
  } else if (outbox.length > 0) {
    moduleStatus = "warning";
    moduleStatusLabel = `${outbox.length} eventos pendientes en la cola local`;
  }

  const handleDownloadInventoryPdf = async () => {
    const defaultReason = selectedStore
      ? `Descarga inventario ${selectedStore.name}`
      : "Descarga inventario corporativo";
    const reason = promptCorporateReason(defaultReason);
    if (reason === null) {
      pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
      return;
    }
    if (reason.length < 5) {
      const message = "El motivo corporativo debe tener al menos 5 caracteres.";
      setError(message);
      pushToast({ message, variant: "error" });
      return;
    }
    try {
      await downloadInventoryReport(reason);
      pushToast({ message: "PDF de inventario descargado", variant: "success" });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible descargar el PDF de inventario.";
      setError(message);
      pushToast({ message, variant: "error" });
    }
  };

  const handleExportCsv = () => {
    const headers = ["id", "entidad", "operacion", "estado", "intentos", "actualizado"];
    const rows = outbox.map((entry) => [
      entry.id,
      `${entry.entity_type} #${entry.entity_id}`,
      entry.operation,
      entry.status,
      entry.attempt_count,
      new Date(entry.updated_at).toLocaleString("es-MX"),
    ]);
    const csvContent = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `sincronizacion_softmobile_${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<Repeat aria-hidden="true" />}
        title="Sincronización"
        subtitle="Control de sincronizaciones locales, respaldos y versiones distribuidas"
        status={moduleStatus}
        statusLabel={moduleStatusLabel}
        actions={
          <button className="btn btn--ghost" type="button" onClick={() => void refreshOutbox()}>
            Refrescar cola
          </button>
        }
      />
      <div className="section-scroll">
        <div className="section-grid">
        <section className="card">
          <h2>Sincronización y reportes</h2>
            <SyncPanel
              onSync={handleSync}
              syncStatus={syncStatus}
              onDownloadPdf={handleDownloadInventoryPdf}
              onBackup={handleBackup}
              onExportCsv={handleExportCsv}
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
              <button className="btn btn--ghost" onClick={refreshOutbox} type="button">
                Actualizar estado
              </button>
              <button
                className="btn btn--primary"
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

        <section className="card">
          <h2>Historial por tienda</h2>
        <p className="card-subtitle">Resumen de las últimas ejecuciones y errores registrados.</p>
        <div className="outbox-actions">
          <button className="btn btn--ghost" type="button" onClick={refreshSyncHistory}>
            Actualizar historial
          </button>
        </div>
        {syncHistoryError ? <p className="error-text">{syncHistoryError}</p> : null}
        {syncHistory.length === 0 ? (
          <p className="muted-text">Aún no hay sesiones registradas.</p>
        ) : (
          <div className="sync-history-grid">
            {syncHistory.map((storeHistory) => (
              <article key={storeHistory.store_id ?? "global"} className="sync-history-item">
                <header>
                  <h3>{storeHistory.store_name}</h3>
                </header>
                <ul>
                  {storeHistory.sessions.map((session) => (
                    <li key={session.id}>
                      <div className="sync-history-line">
                        <span className={`badge ${session.status === "exitoso" ? "success" : "warning"}`}>
                          {session.status === "exitoso" ? "Exitoso" : "Fallido"}
                        </span>
                        <span>{new Date(session.started_at).toLocaleString("es-MX")}</span>
                        <span className="sync-history-mode">Modo: {session.mode}</span>
                      </div>
                      {session.error_message ? (
                        <p className="sync-history-error">⚠️ {session.error_message}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        )}
        </section>

        <section className="card">
          <h2>Sincronización avanzada</h2>
        <p className="card-subtitle">Prioridades por entidad y métricas de reintentos.</p>
        {enableHybridPrep ? (
          outboxStats.length === 0 ? (
            <p className="muted-text">Sin métricas registradas.</p>
          ) : (
            <table className="outbox-stats-table">
              <thead>
                <tr>
                  <th>Entidad</th>
                  <th>Prioridad</th>
                  <th>Total</th>
                  <th>Pendientes</th>
                  <th>Errores</th>
                  <th>Última actualización</th>
                </tr>
              </thead>
              <tbody>
                {outboxStats.map((stat) => (
                  <tr key={`${stat.entity_type}-${stat.priority}`}>
                    <td>{stat.entity_type}</td>
                    <td>
                      <span className={`badge priority-${stat.priority.toLowerCase()}`}>
                        {stat.priority}
                      </span>
                    </td>
                    <td>{stat.total}</td>
                    <td>{stat.pending}</td>
                    <td>{stat.failed}</td>
                    <td>
                      {stat.latest_update
                        ? new Date(stat.latest_update).toLocaleString("es-MX")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : (
          <p className="muted-text">
            Activa la preparación híbrida para obtener métricas de prioridades y reintentos.
          </p>
        )}
        </section>
        </div>
      </div>
    </div>
  );
}

export default SyncPage;
