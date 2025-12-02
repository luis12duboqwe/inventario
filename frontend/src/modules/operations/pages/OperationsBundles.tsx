import { Layers3, PackageSearch } from "lucide-react";

import { useDashboard } from "../../dashboard/context/DashboardContext";

export default function OperationsBundles(): JSX.Element {
  const { enableBundles } = useDashboard();

  if (!enableBundles) {
    return (
      <section className="operations-disabled">
        <h2 className="operations-disabled__title">
          <Layers3 aria-hidden="true" size={20} />
          Paquetes y combos desactivados
        </h2>
        <p className="operations-disabled__text">
          Activa <code>SOFTMOBILE_ENABLE_BUNDLES</code> y asegúrate de que el catálogo pro (
          <code>SOFTMOBILE_ENABLE_CATALOG_PRO</code>) y las operaciones de ventas (
          <code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code>) estén habilitados para poder agrupar
          dispositivos como kits o combos comerciales.
        </p>
      </section>
    );
  }

  return (
    <section className="operations-panel">
      <header className="operations-panel__header">
        <h2 className="operations-panel__title">
          <Layers3 aria-hidden="true" size={20} />
          Catálogo de paquetes activos
        </h2>
        <p className="operations-panel__description">
          Consolida dispositivos y accesorios en combos con precios dinámicos, seguimiento de costos
          y disponibilidad en tiempo real.
        </p>
      </header>
      <article aria-label="Próximos pasos para paquetes" className="operations-article">
        <h3 className="operations-article__title">
          <PackageSearch aria-hidden="true" size={18} />
          Siguientes integraciones
        </h3>
        <ul className="operations-article__list">
          <li>Sincroniza inventario por paquete para reservas y transferencias.</li>
          <li>Define reglas de margen objetivo y alertas de disponibilidad.</li>
          <li>Publica combos destacados en el POS y en el portal comercial.</li>
        </ul>
      </article>
    </section>
  );
}
