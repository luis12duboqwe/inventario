import { Layers3, PackageSearch } from "lucide-react";

import { useDashboard } from "../../dashboard/context/DashboardContext";

export default function OperationsBundles(): JSX.Element {
  const { enableBundles } = useDashboard();

  if (!enableBundles) {
    return (
      <section style={{ display: "grid", gap: 12 }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
          <Layers3 aria-hidden="true" size={20} />
          Paquetes y combos desactivados
        </h2>
        <p style={{ margin: 0, color: "#94a3b8" }}>
          Activa <code>SOFTMOBILE_ENABLE_BUNDLES</code> y asegúrate de que el catálogo
          pro (<code>SOFTMOBILE_ENABLE_CATALOG_PRO</code>) y las operaciones de ventas
          (<code>SOFTMOBILE_ENABLE_PURCHASES_SALES</code>) estén habilitados para poder
          agrupar dispositivos como kits o combos comerciales.
        </p>
      </section>
    );
  }

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 8 }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
          <Layers3 aria-hidden="true" size={20} />
          Catálogo de paquetes activos
        </h2>
        <p style={{ margin: 0, color: "#94a3b8" }}>
          Consolida dispositivos y accesorios en combos con precios dinámicos,
          seguimiento de costos y disponibilidad en tiempo real.
        </p>
      </header>
      <article
        aria-label="Próximos pasos para paquetes"
        style={{
          border: "1px solid rgba(148,163,184,0.25)",
          borderRadius: 12,
          padding: 16,
          display: "grid",
          gap: 8,
          background: "rgba(15,23,42,0.6)",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 16, display: "flex", gap: 8, alignItems: "center" }}>
          <PackageSearch aria-hidden="true" size={18} />
          Siguientes integraciones
        </h3>
        <ul style={{ margin: 0, paddingLeft: 18, color: "#cbd5f5" }}>
          <li>Sincroniza inventario por paquete para reservas y transferencias.</li>
          <li>Define reglas de margen objetivo y alertas de disponibilidad.</li>
          <li>Publica combos destacados en el POS y en el portal comercial.</li>
        </ul>
      </article>
    </section>
  );
}
