import { motion } from "framer-motion";
import { RefreshCcw } from "lucide-react";

import Button from "@components/ui/Button";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

function InventoryMovementsTimelineSection() {
  const {
    module: { recentMovements, recentMovementsLoading, formatCurrency },
    downloads: { triggerRefreshRecentMovements },
  } = useInventoryLayout();

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Últimos movimientos</h2>
          <p className="card-subtitle">Entradas, salidas y ajustes más recientes.</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={triggerRefreshRecentMovements}
          disabled={recentMovementsLoading}
          leadingIcon={<RefreshCcw aria-hidden="true" size={16} />}
        >
          {recentMovementsLoading ? "Actualizando…" : "Actualizar"}
        </Button>
      </header>
      {recentMovementsLoading ? (
        <p className="muted-text">Cargando movimientos recientes…</p>
      ) : recentMovements.length === 0 ? (
        <p className="muted-text">No se registran movimientos en los últimos 14 días.</p>
      ) : (
        <ul className="inventory-timeline">
          {recentMovements.map((movement) => {
            const destination = movement.sucursal_destino ?? "Inventario corporativo";
            const origin = movement.sucursal_origen;
            return (
              <motion.li
                key={movement.id}
                className={`inventory-timeline__item inventory-timeline__item--${movement.tipo_movimiento}`}
                whileHover={{ x: 6 }}
                transition={{ type: "spring", stiffness: 300, damping: 24 }}
              >
                <div className="inventory-timeline__meta">
                  <span className="inventory-timeline__type">{movement.tipo_movimiento.toUpperCase()}</span>
                  <span className="inventory-timeline__date">
                    {new Date(movement.fecha).toLocaleString("es-HN")}
                  </span>
                </div>
                <div className="inventory-timeline__summary">
                  <span>
                    {movement.cantidad.toLocaleString("es-HN")} unidades · {formatCurrency(movement.valor_total)}
                  </span>
                  {movement.usuario ? (
                    <span className="inventory-timeline__user">{movement.usuario}</span>
                  ) : null}
                </div>
                <p className="inventory-timeline__route">
                  {origin ? `${origin} → ${destination}` : destination}
                </p>
                {movement.comentario ? (
                  <p className="inventory-timeline__comment">{movement.comentario}</p>
                ) : null}
              </motion.li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default InventoryMovementsTimelineSection;
