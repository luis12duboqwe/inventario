import AdvancedSearch from "../AdvancedSearch";
import InventoryTable from "../InventoryTable";
import MovementForm from "../MovementForm";
import { useDashboard } from "./DashboardContext";

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

function InventorySection() {
  const {
    token,
    enableCatalogPro,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    selectedStore,
    devices,
    loading,
    totalDevices,
    totalItems,
    totalValue,
    formatCurrency,
    topStores,
    lowStockDevices,
    handleMovement,
    backupHistory,
    updateStatus,
  } = useDashboard();

  const lastBackup = backupHistory.at(0) ?? null;

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
    <div className="section-grid">
      <section className="card">
        <header className="card-header">
          <div>
            <h2>Salud de inventario</h2>
            <p className="card-subtitle">Indicadores clave de todas las tiendas.</p>
          </div>
          {loading ? <span className="pill neutral">Cargando datos…</span> : null}
        </header>
        <div className="status-grid">
          {statusCards.map((cardInfo) => (
            <article key={cardInfo.id} className="status-card">
              <span className="status-card-icon" aria-hidden>
                {cardInfo.icon}
              </span>
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
    </div>
  );
}

export default InventorySection;

