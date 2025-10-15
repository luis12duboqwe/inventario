import { useEffect, useMemo, useState } from "react";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Boxes,
  Building2,
  Cog,
  DollarSign,
  RefreshCcw,
  Search,
  ShieldCheck,
  Smartphone,
  type LucideIcon,
} from "lucide-react";

import AdvancedSearch from "../components/AdvancedSearch";
import InventoryTable from "../components/InventoryTable";
import MovementForm from "../components/MovementForm";
import type { Device } from "../../../api";
import { useInventoryModule } from "../hooks/useInventoryModule";

type StatusBadge = {
  tone: "warning" | "success";
  text: string;
};

type StatusCard = {
  id: string;
  icon: LucideIcon;
  title: string;
  value: string;
  caption: string;
  badge?: StatusBadge;
};

const estadoOptions: Device["estado_comercial"][] = ["nuevo", "A", "B", "C"];

const resolveLowStockSeverity = (quantity: number): "critical" | "warning" | "notice" => {
  if (quantity <= 1) {
    return "critical";
  }
  if (quantity <= 3) {
    return "warning";
  }
  return "notice";
};

function InventoryPage() {
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
    lastInventoryRefresh,
  } = useInventoryModule();

  const [inventoryQuery, setInventoryQuery] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<Device["estado_comercial"] | "TODOS">("TODOS");

  useEffect(() => {
    setInventoryQuery("");
    setEstadoFilter("TODOS");
  }, [selectedStoreId]);

  const lastBackup = backupHistory.at(0) ?? null;
  const lastRefreshDisplay = lastInventoryRefresh
    ? lastInventoryRefresh.toLocaleString("es-MX")
    : "En espera de la primera actualización";

  const filteredDevices = useMemo(() => {
    const normalizedQuery = inventoryQuery.trim().toLowerCase();
    return devices.filter((device) => {
      if (estadoFilter !== "TODOS" && device.estado_comercial !== estadoFilter) {
        return false;
      }
      if (!normalizedQuery) {
        return true;
      }
      const haystack: Array<string | null | undefined> = [
        device.sku,
        device.name,
        device.imei,
        device.serial,
        device.modelo,
        device.marca,
        device.color,
        device.estado_comercial,
      ];
      return haystack.some((value) => {
        if (!value) {
          return false;
        }
        return value.toLowerCase().includes(normalizedQuery);
      });
    });
  }, [devices, estadoFilter, inventoryQuery]);

  const highlightedDevices = useMemo(
    () => new Set(lowStockDevices.map((entry) => entry.device_id)),
    [lowStockDevices],
  );

  const refreshBadge: StatusBadge = lastInventoryRefresh
    ? { tone: "success", text: "Auto" }
    : { tone: "warning", text: "Sin datos" };

  const statusCards: StatusCard[] = [
    {
      id: "stores",
      icon: Building2,
      title: "Sucursales",
      value: `${stores.length}`,
      caption: "Configuradas",
    },
    {
      id: "devices",
      icon: Smartphone,
      title: "Dispositivos",
      value: `${totalDevices}`,
      caption: "Catalogados",
    },
    {
      id: "units",
      icon: Boxes,
      title: "Unidades",
      value: `${totalItems}`,
      caption: "En stock",
    },
    {
      id: "value",
      icon: DollarSign,
      title: "Valor total",
      value: formatCurrency(totalValue),
      caption: "Inventario consolidado",
    },
    {
      id: "backup",
      icon: ShieldCheck,
      title: "Último respaldo",
      value: lastBackup
        ? new Date(lastBackup.executed_at).toLocaleString("es-MX")
        : "Aún no se generan respaldos",
      caption: lastBackup ? lastBackup.mode : "Programado cada 12 h",
    },
    {
      id: "version",
      icon: Cog,
      title: "Versión",
      value: updateStatus?.current_version ?? "Desconocida",
      caption: updateStatus?.latest_version
        ? `Última publicada: ${updateStatus.latest_version}`
        : "Historial actualizado",
      badge: updateStatus?.is_update_available
        ? { tone: "warning", text: `Actualizar a ${updateStatus.latest_version}` }
        : { tone: "success", text: "Sistema al día" },
    },
    {
      id: "refresh",
      icon: RefreshCcw,
      title: "Actualización en vivo",
      value: lastInventoryRefresh
        ? lastInventoryRefresh.toLocaleTimeString("es-MX")
        : "Sincronizando…",
      caption: lastRefreshDisplay,
      badge: refreshBadge,
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
          {statusCards.map((cardInfo) => {
            const Icon = cardInfo.icon;
            return (
              <motion.article
                key={cardInfo.id}
                className="status-card"
                whileHover={{ y: -6, scale: 1.01 }}
                transition={{ type: "spring", stiffness: 260, damping: 20 }}
              >
                <span className="status-card-icon" aria-hidden>
                  <Icon size={26} strokeWidth={1.6} />
                </span>
                <div className="status-card-body">
                  <h3>{cardInfo.title}</h3>
                  <p className="status-value">{cardInfo.value}</p>
                  <span className="status-caption">{cardInfo.caption}</span>
                </div>
                {cardInfo.badge ? (
                  <span className={`badge ${cardInfo.badge.tone}`}>{cardInfo.badge.text}</span>
                ) : null}
              </motion.article>
            );
          })}
        </div>
      </section>

      <section className="card">
        <header className="card-header">
          <h2>Seleccionar sucursal</h2>
        </header>
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
        <header className="card-header">
          <h2>Inventario actual</h2>
          <div className="inventory-meta">
            <span className="muted-text">
              Mostrando {filteredDevices.length} de {devices.length} dispositivos
            </span>
            <span className="inventory-last-update">Última actualización: {lastRefreshDisplay}</span>
          </div>
        </header>
        <div className="inventory-controls">
          <label className="input-with-icon" aria-label="Buscar en inventario">
            <Search size={16} aria-hidden />
            <input
              type="search"
              value={inventoryQuery}
              onChange={(event) => setInventoryQuery(event.target.value)}
              placeholder="Buscar por IMEI, modelo o estado"
            />
          </label>
          <label className="select-inline">
            <span>Estado comercial</span>
            <select
              value={estadoFilter}
              onChange={(event) =>
                setEstadoFilter(event.target.value as Device["estado_comercial"] | "TODOS")
              }
            >
              <option value="TODOS">Todos</option>
              {estadoOptions.map((estado) => (
                <option key={estado} value={estado}>
                  {estado === "nuevo" ? "Nuevo" : `Grado ${estado}`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <InventoryTable
          devices={filteredDevices}
          highlightedDeviceIds={highlightedDevices}
          emptyMessage={
            inventoryQuery.trim() || estadoFilter !== "TODOS"
              ? "No se encontraron dispositivos con los filtros actuales."
              : undefined
          }
        />
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
        <header className="card-header">
          <div>
            <h2>Alertas de inventario bajo</h2>
            <p className="card-subtitle">Seguimiento inmediato de piezas críticas.</p>
          </div>
          <span className={`pill ${lowStockDevices.length === 0 ? "success" : "warning"}`}>
            {lowStockDevices.length === 0
              ? "Sin alertas"
              : `${lowStockDevices.length} alerta${lowStockDevices.length === 1 ? "" : "s"}`}
          </span>
        </header>
        {lowStockDevices.length === 0 ? (
          <p className="muted-text">No hay alertas por ahora.</p>
        ) : (
          <ul className="low-stock-list">
            {lowStockDevices.map((device) => {
              const severity = resolveLowStockSeverity(device.quantity);
              return (
                <motion.li
                  key={device.device_id}
                  className={`low-stock-item ${severity}`}
                  whileHover={{ x: 6 }}
                  transition={{ type: "spring", stiffness: 300, damping: 24 }}
                >
                  <span className="low-stock-icon">
                    <AlertTriangle size={18} />
                  </span>
                  <div className="low-stock-body">
                    <strong>{device.sku}</strong>
                    <span>
                      {device.name} · {device.store_name}
                    </span>
                  </div>
                  <div className="low-stock-meta">
                    <span className="low-stock-quantity">{device.quantity} uds</span>
                    <span>{formatCurrency(device.inventory_value)}</span>
                  </div>
                </motion.li>
              );
            })}
          </ul>
        )}
      </section>

      {enableCatalogPro ? <AdvancedSearch token={token} /> : null}
    </div>
  );
}

export default InventoryPage;

