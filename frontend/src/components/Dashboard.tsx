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
} from "../api";
import InventoryTable from "./InventoryTable";
import MovementForm from "./MovementForm";
import SyncPanel from "./SyncPanel";

type Props = {
  token: string;
};

function Dashboard({ token }: Props) {
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

  return (
    <div className="card" style={{ flex: 1 }}>
      <h2>Panel de operaciones</h2>
      {loading ? <p>Cargando datos iniciales…</p> : null}
      {message ? <p style={{ color: "#4ade80" }}>{message}</p> : null}
      {error ? <p style={{ color: "#f87171" }}>{error}</p> : null}

      <div className="status-grid">
        <div className="status-card">
          <h3>Sucursales</h3>
          <span>{stores.length} configuradas</span>
        </div>
        <div className="status-card">
          <h3>Dispositivos catalogados</h3>
          <span>{totalDevices}</span>
        </div>
        <div className="status-card">
          <h3>Unidades en stock</h3>
          <span>{totalItems}</span>
        </div>
        <div className="status-card">
          <h3>Valor total</h3>
          <span>{formatCurrency(totalValue)}</span>
        </div>
        <div className="status-card">
          <h3>Último respaldo</h3>
          <span>
            {lastBackup
              ? new Date(lastBackup.executed_at).toLocaleString("es-MX")
              : "Aún no se generan respaldos"}
          </span>
        </div>
        <div className="status-card">
          <h3>Versión instalada</h3>
          <span>{updateStatus?.current_version ?? "Desconocida"}</span>
          {updateStatus?.is_update_available ? (
            <p className="badge warning">Actualizar a {updateStatus.latest_version}</p>
          ) : (
            <p className="badge success">Sistema actualizado</p>
          )}
        </div>
      </div>

      <section className="card" style={{ marginTop: 24 }}>
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
          <p style={{ color: "#94a3b8" }}>
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
          <p>No hay datos suficientes para calcular el ranking.</p>
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
        <h2>Sincronización y reportes</h2>
        <SyncPanel
          onSync={handleSync}
          syncStatus={syncStatus}
          onDownloadPdf={() => downloadInventoryPdf(token)}
          onBackup={handleBackup}
        />
        <div style={{ marginTop: 18 }}>
          <h3 style={{ color: "#38bdf8" }}>Historial de respaldos</h3>
          {backupHistory.length === 0 ? (
            <p>No existen respaldos previos.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {backupHistory.map((backup) => (
                <li key={backup.id} style={{ marginBottom: 8 }}>
                  <span className="badge">{backup.mode}</span> · {new Date(backup.executed_at).toLocaleString("es-MX")} · tamaño {(backup.total_size_bytes / 1024).toFixed(1)} KB
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
            <a href={latestRelease.download_url} target="_blank" rel="noreferrer" style={{ marginLeft: 4 }}>
              Descargar instalador
            </a>
          </p>
        ) : (
          <p>No se han publicado versiones en el feed.</p>
        )}
        {releaseHistory.length > 0 ? (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {releaseHistory.map((release) => (
              <li key={release.version} style={{ marginBottom: 8 }}>
                <strong>{release.version}</strong> · {new Date(release.release_date).toLocaleDateString("es-MX")} · {release.notes}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="card">
        <h2>Alertas de inventario bajo</h2>
        {lowStockDevices.length === 0 ? (
          <p>No hay alertas por ahora.</p>
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
    </div>
  );
}

export default Dashboard;
