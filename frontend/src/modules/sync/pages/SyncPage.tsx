import { useCallback, useEffect, useMemo, useState } from "react";
import { Repeat } from "lucide-react";

import SyncPanel from "../components/SyncPanel";
import ModuleHeader, { type ModuleStatus } from "../../../components/ModuleHeader";
import { useSyncModule } from "../hooks/useSyncModule";
import {
  exportSyncConflictsExcel,
  exportSyncConflictsPdf,
  exportTransferReportExcel,
  exportTransferReportPdf,
  getSyncOverview,
  getTransferReport,
  listSyncConflicts,
  listTransfers,
  type SyncBranchOverview,
  type SyncConflictLog,
  type TransferOrder,
  type TransferReport,
} from "../../../api";
import { promptCorporateReason } from "../../../utils/corporateReason";

const transferStatusLabels: Record<TransferOrder["status"], string> = {
  SOLICITADA: "Solicitada",
  EN_TRANSITO: "En tránsito",
  RECIBIDA: "Recibida",
  CANCELADA: "Cancelada",
};

const healthBadgeClass: Record<SyncBranchOverview["health"], string> = {
  operativa: "badge success",
  alerta: "badge warning",
  critica: "badge critical",
  sin_registros: "badge neutral",
};

const severityBadgeClass: Record<SyncConflictLog["severity"], string> = {
  operativa: "badge neutral",
  alerta: "badge warning",
  critica: "badge critical",
  sin_registros: "badge neutral",
};

const moduleStatusBadgeClass: Record<ModuleStatus, string> = {
  ok: "badge success",
  warning: "badge warning",
  critical: "badge critical",
};

const MIN_REASON_LENGTH = 5;

type RecentSyncLog = {
  id: string;
  storeName: string;
  status: string;
  mode: string;
  startedAt: string;
  finishedAt: string | null;
  errorMessage: string | null;
};

function formatDateTime(value?: string | null): string {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleString("es-MX");
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

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
    token,
    stores,
    enableTransfers,
    pushToast,
    setError,
    selectedStore,
    formatCurrency,
  } = useSyncModule();

  const [branchOverview, setBranchOverview] = useState<SyncBranchOverview[]>([]);
  const [overviewLoading, setOverviewLoading] = useState<boolean>(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  const [transfers, setTransfers] = useState<TransferOrder[]>([]);
  const [transferReport, setTransferReport] = useState<TransferReport | null>(null);
  const [transferLoading, setTransferLoading] = useState<boolean>(false);
  const [transferError, setTransferError] = useState<string | null>(null);
  const [exportingTransfers, setExportingTransfers] = useState<boolean>(false);

  const [conflicts, setConflicts] = useState<SyncConflictLog[]>([]);
  const [conflictLoading, setConflictLoading] = useState<boolean>(false);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [exportingConflicts, setExportingConflicts] = useState<boolean>(false);

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

  const storeNameById = useMemo(() => {
    const mapping = new Map<number, string>();
    stores.forEach((store) => {
      mapping.set(store.id, store.name);
    });
    return mapping;
  }, [stores]);

  const formatStoreName = useCallback(
    (storeId: number) => storeNameById.get(storeId) ?? `Sucursal #${storeId}`,
    [storeNameById],
  );

  const requestReason = useCallback(
    (defaultReason: string) => {
      const reason = promptCorporateReason(defaultReason);
      if (reason === null) {
        pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
        return null;
      }
      if (reason.trim().length < MIN_REASON_LENGTH) {
        const message = "El motivo corporativo debe tener al menos 5 caracteres.";
        setError(message);
        pushToast({ message, variant: "error" });
        return null;
      }
      return reason.trim();
    },
    [pushToast, setError],
  );

  const refreshOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await getSyncOverview(token);
      setBranchOverview(data);
      setOverviewError(null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener el estado de las sucursales.";
      setOverviewError(message);
      setError(message);
    } finally {
      setOverviewLoading(false);
    }
  }, [setError, token]);

  const refreshTransfers = useCallback(async () => {
    if (!enableTransfers) {
      setTransfers([]);
      setTransferReport(null);
      return;
    }
    setTransferLoading(true);
    try {
      const [orders, reportData] = await Promise.all([
        listTransfers(token),
        getTransferReport(token),
      ]);
      setTransfers(orders.slice(0, 8));
      setTransferReport(reportData);
      setTransferError(null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible obtener las transferencias recientes.";
      setTransferError(message);
      setError(message);
    } finally {
      setTransferLoading(false);
    }
  }, [enableTransfers, setError, token]);

  const refreshConflicts = useCallback(async () => {
    setConflictLoading(true);
    try {
      const data = await listSyncConflicts(token, { limit: 25 });
      setConflicts(data);
      setConflictError(null);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No fue posible cargar los conflictos de sincronización.";
      setConflictError(message);
      setError(message);
    } finally {
      setConflictLoading(false);
    }
  }, [setError, token]);

  useEffect(() => {
    void refreshOverview();
  }, [refreshOverview]);

  useEffect(() => {
    void refreshTransfers();
  }, [refreshTransfers]);

  useEffect(() => {
    void refreshConflicts();
  }, [refreshConflicts]);

  const handleDownloadInventoryPdf = async () => {
    const defaultReason = selectedStore
      ? `Descarga inventario ${selectedStore.name}`
      : "Descarga inventario corporativo";
    const reason = requestReason(defaultReason);
    if (!reason) {
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
    downloadBlob(blob, `sincronizacion_softmobile_${new Date().toISOString()}.csv`);
  };

  const handleExportTransfers = async (format: "pdf" | "xlsx") => {
    if (!enableTransfers) {
      pushToast({ message: "Las transferencias están deshabilitadas.", variant: "info" });
      return;
    }
    const reason = requestReason("Reporte central de transferencias");
    if (!reason) {
      return;
    }
    setExportingTransfers(true);
    try {
      const exporter = format === "pdf" ? exportTransferReportPdf : exportTransferReportExcel;
      const blob = await exporter(token, reason);
      const filename = `transferencias_${new Date()
        .toISOString()
        .replace(/[.:]/g, "-")}.${format === "pdf" ? "pdf" : "xlsx"}`;
      downloadBlob(blob, filename);
      pushToast({
        message: `Reporte de transferencias en formato ${format.toUpperCase()} generado`,
        variant: "success",
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : `No fue posible exportar las transferencias en formato ${format.toUpperCase()}.`;
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setExportingTransfers(false);
    }
  };

  const handleExportConflicts = async (format: "pdf" | "xlsx") => {
    const reason = requestReason("Reporte de conflictos de sincronización");
    if (!reason) {
      return;
    }
    setExportingConflicts(true);
    try {
      const exporter = format === "pdf" ? exportSyncConflictsPdf : exportSyncConflictsExcel;
      const blob = await exporter(token, reason, { limit: 200 });
      const filename = `conflictos_sync_${new Date()
        .toISOString()
        .replace(/[.:]/g, "-")}.${format === "pdf" ? "pdf" : "xlsx"}`;
      downloadBlob(blob, filename);
      pushToast({
        message: `Reporte de conflictos en formato ${format.toUpperCase()} generado`,
        variant: "success",
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : `No fue posible exportar los conflictos en formato ${format.toUpperCase()}.`;
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setExportingConflicts(false);
    }
  };

  const totalInventoryValue = useMemo(() => {
    return branchOverview.reduce((acc, item) => acc + Number(item.inventory_value || 0), 0);
  }, [branchOverview]);

  const totalPendingTransfers = useMemo(() => {
    return branchOverview.reduce((acc, item) => acc + item.pending_transfers, 0);
  }, [branchOverview]);

  const totalOpenConflicts = useMemo(() => {
    return branchOverview.reduce((acc, item) => acc + item.open_conflicts, 0);
  }, [branchOverview]);

  const recentSyncLogs = useMemo<RecentSyncLog[]>(() => {
    return syncHistory
      .flatMap((storeHistory) =>
        storeHistory.sessions.map((session) => ({
          id: `${storeHistory.store_id ?? "global"}-${session.id}`,
          storeName: storeHistory.store_name,
          status: session.status,
          mode: session.mode,
          startedAt: session.started_at,
          finishedAt: session.finished_at ?? null,
          errorMessage: session.error_message ?? null,
        })),
      )
      .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
      .slice(0, 6);
  }, [syncHistory]);

  const lastSyncExecution = recentSyncLogs.length > 0 ? recentSyncLogs[0] : null;

  const transferReportItems = useMemo(() => {
    return transferReport ? transferReport.items.slice(0, 6) : [];
  }, [transferReport]);

  const extraTransferItems = useMemo(() => {
    if (!transferReport) {
      return 0;
    }
    return Math.max(transferReport.items.length - transferReportItems.length, 0);
  }, [transferReport, transferReportItems]);

  const currentSyncLabel = syncStatus ?? moduleStatusLabel;
  const totalPendingOutbox = outbox.length;

  const topConflicts = useMemo(() => conflicts.slice(0, 6), [conflicts]);

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
          <section className="card sync-dashboard">
            <div className="sync-dashboard__header">
              <h2>Dashboard de sincronización</h2>
              <span className={moduleStatusBadgeClass[moduleStatus]}>{moduleStatusLabel}</span>
            </div>
            <div className="sync-dashboard__summary">
              <div className="sync-metric">
                <span>Estado actual</span>
                <strong>{currentSyncLabel}</strong>
                <small>
                  {hasSyncFailure
                    ? "Atiende los errores pendientes para recuperar la sincronización"
                    : "Monitoreo híbrido en ejecución"}
                </small>
              </div>
              <div className="sync-metric">
                <span>Última ejecución</span>
                <strong>{lastSyncExecution ? formatDateTime(lastSyncExecution.startedAt) : "Sin registros"}</strong>
                <small>
                  {lastSyncExecution
                    ? `${lastSyncExecution.storeName} · ${lastSyncExecution.mode}`
                    : "Ejecuta una sincronización manual para registrar actividad"}
                </small>
              </div>
              <div className="sync-metric">
                <span>Sucursales monitoreadas</span>
                <strong>{branchOverview.length}</strong>
                <small>{branchOverview.length === 1 ? "1 tienda activa" : `${branchOverview.length} tiendas activas`}</small>
              </div>
              <div className="sync-metric">
                <span>Inventario monitoreado</span>
                <strong>{branchOverview.length > 0 ? formatCurrency(totalInventoryValue) : "—"}</strong>
                <small>Valor acumulado por sucursal</small>
              </div>
              <div className="sync-metric">
                <span>Cola local pendiente</span>
                <strong>{totalPendingOutbox}</strong>
                <small>{enableHybridPrep ? "Eventos por replicar" : "Habilita el modo híbrido"}</small>
              </div>
              <div className="sync-metric">
                <span>Conflictos abiertos</span>
                <strong>{totalOpenConflicts}</strong>
                <small>{totalOpenConflicts === 1 ? "Un conflicto detectado" : "Conflictos por resolver"}</small>
              </div>
              <div className="sync-metric">
                <span>Transferencias activas</span>
                <strong>{totalPendingTransfers}</strong>
                <small>Solicitadas o en tránsito</small>
              </div>
            </div>
            <div className="sync-dashboard__logs">
              <h3>Últimos registros</h3>
              {recentSyncLogs.length === 0 ? (
                <p className="muted-text">Sin ejecuciones registradas en la bitácora.</p>
              ) : (
                <ul className="sync-log-list">
                  {recentSyncLogs.map((log) => (
                    <li key={log.id} className="sync-log__item">
                      <div className="sync-log__header">
                        <div
                          className={`badge ${log.status === "exitoso" ? "success" : "warning"}`}
                          aria-label={log.status === "exitoso" ? "Ejecución exitosa" : "Ejecución con fallos"}
                        >
                          {log.status === "exitoso" ? "Exitoso" : "Fallido"}
                        </div>
                        <span className="sync-log__time">{formatDateTime(log.startedAt)}</span>
                      </div>
                      <div className="sync-log__meta">
                        <span>{log.storeName}</span>
                        <span>Modo: {log.mode}</span>
                        {log.finishedAt ? <span>Finalizó {formatDateTime(log.finishedAt)}</span> : null}
                      </div>
                      {log.errorMessage ? (
                        <p className="sync-log__error">⚠️ {log.errorMessage}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <h2>Panorama de sucursales</h2>
              <button
                className="btn btn--ghost"
                type="button"
                onClick={() => void refreshOverview()}
                disabled={overviewLoading}
              >
                Actualizar
              </button>
            </div>
            {overviewError ? <p className="error-text">{overviewError}</p> : null}
            {overviewLoading ? (
              <p className="muted-text">Cargando estado de sucursales…</p>
            ) : branchOverview.length === 0 ? (
              <p className="muted-text">Aún no se registran sucursales en el sistema.</p>
            ) : (
              <div className="table-responsive">
                <table className="sync-branch-table">
                  <thead>
                    <tr>
                      <th>Sucursal</th>
                      <th>Estado</th>
                      <th>Última sincronización</th>
                      <th>Transferencias pendientes</th>
                      <th>Conflictos</th>
                      <th>Inventario</th>
                    </tr>
                  </thead>
                  <tbody>
                    {branchOverview.map((store) => (
                      <tr key={store.store_id}>
                        <td>
                          <div className="sync-branch-name">
                            <strong>{store.store_name}</strong>
                            <span className="muted-text">Código {store.store_code}</span>
                          </div>
                        </td>
                        <td>
                          <span className={healthBadgeClass[store.health]}> {store.health_label}</span>
                        </td>
                        <td>{formatDateTime(store.last_sync_at)}</td>
                        <td>{store.pending_transfers}</td>
                        <td>{store.open_conflicts}</td>
                        <td>{formatCurrency(Number(store.inventory_value || 0))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {branchOverview.length > 0 ? (
              <div className="branch-summary">
                <span>
                  Total inventario monitoreado: <strong>{formatCurrency(totalInventoryValue)}</strong>
                </span>
                <span>
                  Transferencias activas: <strong>{totalPendingTransfers}</strong>
                </span>
                <span>
                  Sucursales registradas: <strong>{stores.length}</strong>
                </span>
              </div>
            ) : null}
          </section>

          <section className="card">
            <div className="card-header">
              <h2>Transferencias entre tiendas</h2>
              <div className="card-actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void refreshTransfers()}
                  disabled={transferLoading}
                >
                  Actualizar
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleExportTransfers("pdf")}
                  disabled={exportingTransfers}
                >
                  Exportar PDF
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleExportTransfers("xlsx")}
                  disabled={exportingTransfers}
                >
                  Exportar Excel
                </button>
              </div>
            </div>
            {transferError ? <p className="error-text">{transferError}</p> : null}
            {!enableTransfers ? (
              <p className="muted-text">La funcionalidad de transferencias está desactivada en esta instancia.</p>
            ) : transferLoading ? (
              <p className="muted-text">Cargando transferencias recientes…</p>
            ) : (
              <>
                {transferReport ? (
                  <div className="transfer-totals">
                    <div>
                      <span className="muted-text">Totales</span>
                      <strong>{transferReport.totals.total_transfers}</strong>
                    </div>
                    <div>
                      <span className="muted-text">Pendientes</span>
                      <strong>{transferReport.totals.pending}</strong>
                    </div>
                    <div>
                      <span className="muted-text">En tránsito</span>
                      <strong>{transferReport.totals.in_transit}</strong>
                    </div>
                    <div>
                      <span className="muted-text">Completadas</span>
                      <strong>{transferReport.totals.completed}</strong>
                    </div>
                    <div>
                      <span className="muted-text">Canceladas</span>
                      <strong>{transferReport.totals.cancelled}</strong>
                    </div>
                    <div>
                      <span className="muted-text">Dispositivos movilizados</span>
                      <strong>{transferReport.totals.total_quantity}</strong>
                    </div>
                  </div>
                ) : null}
                {transfers.length === 0 ? (
                  <p className="muted-text">No hay transferencias registradas.</p>
                ) : (
                  <ul className="transfer-list">
                    {transfers.map((transfer) => (
                      <li key={transfer.id}>
                        <div className={`badge transfer-${transfer.status.toLowerCase()}`}>
                          {transferStatusLabels[transfer.status]}
                        </div>
                        <div className="transfer-body">
                          <p>
                            <strong>
                              {formatStoreName(transfer.origin_store_id)} → {formatStoreName(transfer.destination_store_id)}
                            </strong>
                          </p>
                          <p className="muted-text">
                            Registrada el {formatDateTime(transfer.created_at)}
                          </p>
                          {transfer.reason ? (
                            <p className="muted-text">Motivo: {transfer.reason}</p>
                          ) : null}
                          <p className="muted-text">
                            Artículos: {transfer.items.reduce((acc, item) => acc + item.quantity, 0)}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
                {transferReportItems.length > 0 ? (
                  <div className="table-responsive transfer-details-table">
                    <table>
                      <thead>
                        <tr>
                          <th>Folio</th>
                          <th>Origen</th>
                          <th>Destino</th>
                          <th>Estado</th>
                          <th>Productos y cantidades</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transferReportItems.map((item) => (
                          <tr key={item.id}>
                            <td>
                              <div className="transfer-meta">
                                <strong>{item.folio}</strong>
                                <span className="muted-text">{formatDateTime(item.requested_at)}</span>
                              </div>
                            </td>
                            <td>{item.origin_store}</td>
                            <td>{item.destination_store}</td>
                            <td>
                              <span className={`badge transfer-${item.status.toLowerCase()}`}>
                                {transferStatusLabels[item.status]}
                              </span>
                            </td>
                            <td>
                              {item.devices.length === 0 ? (
                                <span className="muted-text">Sin productos registrados</span>
                              ) : (
                                <ul className="transfer-devices">
                                  {item.devices.map((device, index) => (
                                    <li key={`${item.id}-${device.sku ?? device.name ?? index}-${index}`}>
                                      <span className="transfer-device-name">{device.name ?? "Producto"}</span>
                                      {device.sku ? (
                                        <span className="transfer-device-sku">SKU {device.sku}</span>
                                      ) : null}
                                      <span className="transfer-device-qty">×{device.quantity}</span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                {extraTransferItems > 0 ? (
                  <p className="muted-text transfer-details-footnote">
                    Se muestran las últimas {transferReportItems.length} transferencias. Descarga el reporte para ver las {" "}
                    {transferReport?.items.length} registradas.
                  </p>
                ) : null}
              </>
            )}
          </section>

          <section className="card">
            <div className="card-header">
              <h2>Conflictos de sincronización</h2>
              <div className="card-actions">
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void refreshConflicts()}
                  disabled={conflictLoading}
                >
                  Actualizar
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleExportConflicts("pdf")}
                  disabled={exportingConflicts}
                >
                  Exportar PDF
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => void handleExportConflicts("xlsx")}
                  disabled={exportingConflicts}
                >
                  Exportar Excel
                </button>
              </div>
            </div>
            {conflictError ? <p className="error-text">{conflictError}</p> : null}
            {conflictLoading ? (
              <p className="muted-text">Analizando discrepancias…</p>
            ) : topConflicts.length === 0 ? (
              <p className="muted-text">No hay conflictos detectados recientemente.</p>
            ) : (
              <ul className="conflict-list">
                {topConflicts.map((conflict) => (
                  <li key={conflict.id}>
                    <div className={severityBadgeClass[conflict.severity]}>{conflict.severity.toUpperCase()}</div>
                    <div className="conflict-body">
                      <p>
                        <strong>{conflict.sku}</strong> · {conflict.product_name ?? "Sin descripción"}
                      </p>
                      <p className="muted-text">Diferencia detectada: {conflict.difference}</p>
                      <p className="muted-text">Detectado el {formatDateTime(conflict.detected_at)}</p>
                      <div className="conflict-stores">
                        <span>
                          Máximo: {conflict.stores_max.map((item) => `${item.store_name} (${item.quantity})`).join(", ") || "—"}
                        </span>
                        <span>
                          Mínimo: {conflict.stores_min.map((item) => `${item.store_name} (${item.quantity})`).join(", ") || "—"}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

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
                      <span>{formatDateTime(backup.executed_at)}</span>
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
                La sincronización híbrida está desactivada. Ajusta el flag <code>SOFTMOBILE_ENABLE_HYBRID_PREP</code> para
                habilitar la cola local.
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
                            <span>{formatDateTime(session.started_at)}</span>
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
                      <tr key={`${stat.entity_type}-${stat.priority.toLowerCase()}`}>
                        <td>{stat.entity_type}</td>
                        <td>
                          <span className={`badge priority-${stat.priority.toLowerCase()}`}>
                            {stat.priority}
                          </span>
                        </td>
                        <td>{stat.total}</td>
                        <td>{stat.pending}</td>
                        <td>{stat.failed}</td>
                        <td>{stat.latest_update ? formatDateTime(stat.latest_update) : "—"}</td>
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
