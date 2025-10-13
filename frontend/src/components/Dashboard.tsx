import { useEffect, useMemo, useState } from "react";
import type {
  BackupJob,
  Device,
  InventoryMetrics,
  MovementInput,
  Store,
  Summary,
  ReleaseInfo,
  UpdateStatus,
  SyncOutboxEntry,
} from "../api";
import {
  downloadInventoryPdf,
  fetchBackupHistory,
  getDevices,
  getStores,
  getSummary,
  getReleaseHistory,
  getUpdateStatus,
  getInventoryMetrics,
  registerMovement,
  runBackup,
  triggerSync,
  listSyncOutbox,
  retrySyncOutbox,
} from "../api";
import InventoryTable from "./InventoryTable";
import MovementForm from "./MovementForm";
import SyncPanel from "./SyncPanel";
import AdvancedSearch from "./AdvancedSearch";
import TransferOrders from "./TransferOrders";
import Purchases from "./Purchases";
import Sales from "./Sales";
import Returns from "./Returns";
import AnalyticsBoard from "./AnalyticsBoard";
import TwoFactorSetup from "./TwoFactorSetup";
import AuditLog from "./AuditLog";

type Props = {
  token: string;
};

type StatusBadge = {
  tone: "warning" | "success";
  text: string;
};

type StatusCard = {
  id: string;
  icon: string;
  title: string;
  value: string;
  caption: string;
  badge?: StatusBadge;
};

function Dashboard({ token }: Props) {
  const enableCatalogPro =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_CATALOG_PRO ?? "1") !== "0";
  const enableTransfers =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_TRANSFERS ?? "1") !== "0";
  const enablePurchasesSales =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_PURCHASES_SALES ?? "1") !== "0";
  const enableAnalyticsAdv =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_ANALYTICS_ADV ?? "1") !== "0";
  const enableTwoFactor =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_2FA ?? "0") !== "0";
  const enableHybridPrep =
    (import.meta.env.VITE_SOFTMOBILE_ENABLE_HYBRID_PREP ?? "1") !== "0";
  const [stores, setStores] = useState<Store[]>([]);
  const [summary, setSummary] = useState<Summary[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [backupHistory, setBackupHistory] = useState<BackupJob[]>([]);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus | null>(null);
  const [releaseHistory, setReleaseHistory] = useState<ReleaseInfo[]>([]);
  const [metrics, setMetrics] = useState<InventoryMetrics | null>(null);
  const [outbox, setOutbox] = useState<SyncOutboxEntry[]>([]);
  const [outboxError, setOutboxError] = useState<string | null>(null);

  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );
  const formatCurrency = (value: number) => currencyFormatter.format(value);

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === selectedStoreId) ?? null,
    [stores, selectedStoreId]
  );

  useEffect(() => {
    const fetchInitial = async () => {
      try {
        setLoading(true);
        const [storesData, summaryData, metricsData, backupData, statusData, releasesData] = await Promise.all([
          getStores(token),
          getSummary(token),
          getInventoryMetrics(token),
          fetchBackupHistory(token),
          getUpdateStatus(token),
          getReleaseHistory(token),
        ]);
        setStores(storesData);
        setSummary(summaryData);
        setMetrics(metricsData);
        setBackupHistory(backupData);
        setUpdateStatus(statusData);
        setReleaseHistory(releasesData);
        if (storesData.length > 0) {
          setSelectedStoreId(storesData[0].id);
          const devicesData = await getDevices(token, storesData[0].id);
          setDevices(devicesData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los datos iniciales");
      } finally {
        setLoading(false);
      }
    };

    fetchInitial();
  }, [token]);

  useEffect(() => {
    const loadDevices = async () => {
      if (!selectedStoreId) {
        setDevices([]);
        return;
      }
      try {
        const devicesData = await getDevices(token, selectedStoreId);
        setDevices(devicesData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar los dispositivos");
      }
    };

    loadDevices();
  }, [selectedStoreId, token]);

  useEffect(() => {
    const loadOutbox = async () => {
      if (!enableHybridPrep) {
        setOutbox([]);
        return;
      }
      try {
        const entries = await listSyncOutbox(token);
        setOutbox(entries);
        setOutboxError(null);
      } catch (err) {
        setOutboxError(err instanceof Error ? err.message : "No fue posible consultar la cola de sincronización");
      }
    };

    loadOutbox();
  }, [enableHybridPrep, token]);

  const refreshSummary = async () => {
    const [summaryData, metricsData] = await Promise.all([
      getSummary(token),
      getInventoryMetrics(token),
    ]);
    setSummary(summaryData);
    setMetrics(metricsData);
  };

  const handleMovement = async (payload: MovementInput) => {
    if (!selectedStoreId) {
      return;
    }
    try {
      setError(null);
      await registerMovement(token, selectedStoreId, payload);
      setMessage("Movimiento registrado correctamente");
      await Promise.all([refreshSummary(), getDevices(token, selectedStoreId).then(setDevices)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar el movimiento");
    }
  };

  const refreshInventoryAfterTransfer = async () => {
    await refreshSummary();
    if (selectedStoreId) {
      const devicesData = await getDevices(token, selectedStoreId);
      setDevices(devicesData);
    }
  };

  const handleSync = async () => {
    try {
      setSyncStatus("Sincronizando…");
      await triggerSync(token, selectedStoreId ?? undefined);
      setSyncStatus("Sincronización completada");
    } catch (err) {
      setSyncStatus(err instanceof Error ? err.message : "Error durante la sincronización");
    }
  };

  const handleBackup = async () => {
    try {
      setError(null);
      const job = await runBackup(token, "Respaldo manual desde tienda");
      setBackupHistory((current) => [job, ...current].slice(0, 10));
      setMessage("Respaldo generado y almacenado en el servidor central");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el respaldo");
    }
  };

  const refreshOutbox = async () => {
    if (!enableHybridPrep) {
      return;
    }
    try {
      const entries = await listSyncOutbox(token);
      setOutbox(entries);
      setOutboxError(null);
    } catch (err) {
      setOutboxError(err instanceof Error ? err.message : "No se pudo actualizar la cola local");
    }
  };

  const handleRetryOutbox = async () => {
    if (!enableHybridPrep || outbox.length === 0) {
      return;
    }
    try {
      setOutboxError(null);
      const updated = await retrySyncOutbox(
        token,
        outbox.map((entry) => entry.id),
        "Reintento manual desde panel"
      );
      setOutbox(updated);
      setMessage("Eventos listos para reintento local");
    } catch (err) {
      setOutboxError(err instanceof Error ? err.message : "No se pudo reagendar la cola local");
    }
  };

  const totalDevices = useMemo(
    () => metrics?.totals.devices ?? summary.reduce((acc, store) => acc + store.devices.length, 0),
    [metrics, summary]
  );
  const totalItems = useMemo(
    () => metrics?.totals.total_units ?? summary.reduce((acc, store) => acc + store.total_items, 0),
    [metrics, summary]
  );
  const totalValue = useMemo(
    () =>
      metrics?.totals.total_value ??
      summary.reduce(
        (acc, store) => acc + store.devices.reduce((deviceAcc, device) => deviceAcc + device.inventory_value, 0),
        0
      ),
    [metrics, summary]
  );
  const lastBackup = backupHistory.at(0) ?? null;
  const latestRelease = updateStatus?.latest_release ?? null;
  const lowStockDevices = metrics?.low_stock_devices ?? [];
  const topStores = metrics?.top_stores ?? [];

  const statusCards: StatusCard[] = [
    {
      id: "stores",
      icon: "🏢",
      title: "Sucursales",
      value: `${stores.length}`,
      caption: "Configuradas",
    },
    {
      id: "devices",
      icon: "📱",
      title: "Dispositivos",
      value: `${totalDevices}`,
      caption: "Catalogados",
    },
    {
      id: "units",
      icon: "📦",
      title: "Unidades",
      value: `${totalItems}`,
      caption: "En stock",
    },
    {
      id: "value",
      icon: "💰",
      title: "Valor total",
      value: formatCurrency(totalValue),
      caption: "Inventario consolidado",
    },
    {
      id: "backup",
      icon: "🛡️",
      title: "Último respaldo",
      value: lastBackup
        ? new Date(lastBackup.executed_at).toLocaleString("es-MX")
        : "Aún no se generan respaldos",
      caption: lastBackup ? lastBackup.mode : "Programado cada 12 h",
    },
    {
      id: "version",
      icon: "⚙️",
      title: "Versión",
      value: updateStatus?.current_version ?? "Desconocida",
      caption: updateStatus?.latest_version
        ? `Última: ${updateStatus.latest_version}`
        : "Historial actualizado",
      badge: updateStatus?.is_update_available
        ? { tone: "warning" as const, text: `Actualizar a ${updateStatus.latest_version}` }
        : { tone: "success" as const, text: "Sistema al día" },
    },
  ];

  return (
    <div className="dashboard">
      <section className="card">
        <header className="card-header">
          <div>
            <h2>Panel de operaciones</h2>
            <p className="card-subtitle">Monitorea el pulso de las tiendas en tiempo real.</p>
          </div>
          {loading ? <span className="pill neutral">Cargando datos iniciales…</span> : null}
        </header>
        {message ? <div className="alert success">{message}</div> : null}
        {error ? <div className="alert error">{error}</div> : null}

        <div className="status-grid">
          {statusCards.map((cardInfo) => (
            <article key={cardInfo.id} className="status-card">
              <span className="status-card-icon" aria-hidden>{cardInfo.icon}</span>
              <div className="status-card-body">
                <h3>{cardInfo.title}</h3>
                <p className="status-value">{cardInfo.value}</p>
                <span className="status-caption">{cardInfo.caption}</span>
              </div>
              {cardInfo.badge ? <span className={`badge ${cardInfo.badge.tone}`}>{cardInfo.badge.text}</span> : null}
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Seleccionar sucursal</h2>
        <select
          value={selectedStoreId ?? ""}
          onChange={(event) => setSelectedStoreId(event.target.value ? Number(event.target.value) : null)}
        >
          {stores.map((store) => (
            <option key={store.id} value={store.id}>
              {store.name}
            </option>
          ))}
        </select>
        {selectedStore ? (
          <p className="muted-text">
            {selectedStore.location ? `${selectedStore.location} · ` : ""}
            Zona horaria: {selectedStore.timezone}
          </p>
        ) : null}
      </section>

      <section className="card">
        <h2>Inventario actual</h2>
        <InventoryTable devices={devices} />
      </section>

      <section className="card">
        <h2>Top sucursales por valor</h2>
        {topStores.length === 0 ? (
          <p className="muted-text">No hay datos suficientes para calcular el ranking.</p>
        ) : (
          <ul className="metrics-list">
            {topStores.map((storeMetric) => (
              <li key={storeMetric.store_id}>
                <strong>{storeMetric.store_name}</strong> · {storeMetric.device_count} dispositivos · {storeMetric.total_units}
                unidades ·<span> {formatCurrency(storeMetric.total_value)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Registrar movimiento</h2>
        <MovementForm devices={devices} onSubmit={handleMovement} />
      </section>

      <section className="card">
        <h2>
          <span role="img" aria-label="reportes">
            🗂
          </span>{" "}
          Sincronización y reportes
        </h2>
        <SyncPanel
          onSync={handleSync}
          syncStatus={syncStatus}
          onDownloadPdf={() => downloadInventoryPdf(token)}
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
        <h2>Alertas de inventario bajo</h2>
        {lowStockDevices.length === 0 ? (
          <p className="muted-text">No hay alertas por ahora.</p>
        ) : (
          <ul className="metrics-list">
            {lowStockDevices.map((device) => (
              <li key={device.device_id}>
                <strong>{device.sku}</strong> · {device.name} ({device.quantity} uds) — {device.store_name} ·
                <span> {formatCurrency(device.inventory_value)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      {enableCatalogPro ? <AdvancedSearch token={token} /> : null}
      {enableAnalyticsAdv ? <AnalyticsBoard token={token} /> : null}
      {enableHybridPrep ? (
        <section className="card">
          <h2>Cola de sincronización local</h2>
          <p className="card-subtitle">Eventos pendientes de envío a la nube corporativa.</p>
          <div className="outbox-actions">
            <button className="btn" onClick={refreshOutbox}>
              Actualizar estado
            </button>
            <button className="btn ghost" onClick={handleRetryOutbox} disabled={outbox.length === 0}>
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
                    <td>{new Date(entry.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : null}
      {enableTwoFactor ? <TwoFactorSetup token={token} /> : null}
      <AuditLog token={token} />
      {enablePurchasesSales ? (
        <>
          <Purchases
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
          <Sales
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
          <Returns
            token={token}
            stores={stores}
            defaultStoreId={selectedStoreId}
            onInventoryRefresh={refreshInventoryAfterTransfer}
          />
        </>
      ) : null}
      {enableTransfers ? (
        <TransferOrders
          token={token}
          stores={stores}
          defaultOriginId={selectedStoreId}
          onRefreshInventory={refreshInventoryAfterTransfer}
        />
      ) : null}
    </div>
  );
}

export default Dashboard;
