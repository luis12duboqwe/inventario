import { Suspense, lazy } from "react";

import { motion } from "framer-motion";

import { Loader } from "@components/ui/Loader";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

const InventoryCategoryChart = lazy(() => import("../../components/InventoryCategoryChart"));

function InventoryStatusSection() {
  const {
    module: {
      stores,
      selectedStoreId,
      setSelectedStoreId,
      selectedStore,
      formatCurrency,
      topStores,
      storeValuationSnapshot,
      stockByCategory,
    },
    metrics: { statusCards, totalCategoryUnits },
  } = useInventoryLayout();

  return (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Salud de inventario</h2>
            <p className="card-subtitle">Indicadores clave de todas las tiendas.</p>
          </div>
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
          <div>
            <h2>Seleccionar sucursal</h2>
            <p className="card-subtitle">Ajusta el análisis para una tienda específica.</p>
          </div>
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

      {storeValuationSnapshot ? (
        <section className="card">
          <header className="card-header">
            <div>
              <h2>Conciliación contable</h2>
              <p className="card-subtitle">
                Valor registrado vs. calculado en {storeValuationSnapshot.storeName}.
              </p>
            </div>
            <span
              className={`pill ${
                storeValuationSnapshot.hasRelevantDifference ? "warning" : "success"
              }`}
            >
              {storeValuationSnapshot.hasRelevantDifference ? "Revisión requerida" : "Sin diferencias"}
            </span>
          </header>
          <ul className="metrics-list">
            <li>
              <strong>Valor contable registrado</strong>
              <span>{formatCurrency(storeValuationSnapshot.registeredValue)}</span>
            </li>
            <li>
              <strong>Valor operativo calculado</strong>
              <span>{formatCurrency(storeValuationSnapshot.calculatedValue)}</span>
            </li>
            <li>
              <strong>Diferencia neta</strong>
              <span>{formatCurrency(storeValuationSnapshot.difference)}</span>
            </li>
            {storeValuationSnapshot.differencePercent !== null ? (
              <li>
                <strong>Variación porcentual</strong>
                <span>{`${Math.abs(storeValuationSnapshot.differencePercent).toFixed(2)} %`}</span>
              </li>
            ) : null}
          </ul>
          <p className="muted-text">
            {storeValuationSnapshot.hasRelevantDifference
              ? `El valor calculado es ${
                  storeValuationSnapshot.difference > 0 ? "mayor" : "menor"
                } que el contable por ${formatCurrency(Math.abs(storeValuationSnapshot.difference))}.`
              : "Los valores coinciden con el registro contable corporativo."}
          </p>
        </section>
      ) : null}

      <section className="card">
        <header className="card-header">
          <div>
            <h2>Top sucursales por valor</h2>
            <p className="card-subtitle">Ranking de tiendas por cantidad y valuación.</p>
          </div>
        </header>
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

      <section className="card chart-card">
        <header className="card-header">
          <div>
            <h2>Stock por categoría</h2>
            <p className="card-subtitle">Visualiza la distribución de existencias en inventario.</p>
          </div>
          <span className="pill neutral">
            Total {totalCategoryUnits.toLocaleString("es-HN")}
            {" "}uds
          </span>
        </header>
        <Suspense fallback={<Loader label="Cargando gráfica por categoría…" variant="spinner" />}>
          <InventoryCategoryChart data={stockByCategory} totalUnits={totalCategoryUnits} />
        </Suspense>
      </section>
    </div>
  );
}

export default InventoryStatusSection;
