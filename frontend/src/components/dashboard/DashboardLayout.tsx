import { useEffect, useMemo, useState } from "react";
import { useDashboard } from "./DashboardContext";
import InventorySection from "./InventorySection";
import OperationsSection from "./OperationsSection";
import AnalyticsSection from "./AnalyticsSection";
import SecuritySection from "./SecuritySection";
import SyncSection from "./SyncSection";

type SectionKey = "inventory" | "operations" | "analytics" | "security" | "sync";

type SectionDefinition = {
  key: SectionKey;
  label: string;
  isEnabled: boolean;
  element: JSX.Element;
};

const DEFAULT_SECTION: SectionKey = "inventory";

function DashboardLayout() {
  const {
    enableAnalyticsAdv,
    enablePurchasesSales,
    enableTransfers,
    message,
    error,
    setMessage,
    setError,
  } = useDashboard();
  const [active, setActive] = useState<SectionKey>(DEFAULT_SECTION);

  const sections: SectionDefinition[] = useMemo(
    () => [
      { key: "inventory", label: "Inventario", isEnabled: true, element: <InventorySection /> },
      {
        key: "operations",
        label: "Operaciones",
        isEnabled: enablePurchasesSales || enableTransfers,
        element: <OperationsSection />,
      },
      {
        key: "analytics",
        label: "Analítica",
        isEnabled: enableAnalyticsAdv,
        element: <AnalyticsSection />,
      },
      { key: "security", label: "Seguridad", isEnabled: true, element: <SecuritySection /> },
      { key: "sync", label: "Sincronización", isEnabled: true, element: <SyncSection /> },
    ],
    [enableAnalyticsAdv, enablePurchasesSales, enableTransfers]
  );

  const availableSections = sections.filter((section) => section.isEnabled);

  useEffect(() => {
    if (!availableSections.some((section) => section.key === active) && availableSections.length > 0) {
      setActive(availableSections[0].key);
    }
  }, [active, availableSections]);

  const activeSection =
    availableSections.find((section) => section.key === active) ?? availableSections[0] ?? sections[0];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Softmobile 2025 · Centro de control</h1>
        <p className="muted-text">
          Gestiona inventario, operaciones y seguridad desde áreas especializadas.
        </p>
      </header>
      <nav className="dashboard-nav" aria-label="Secciones del panel">
        {availableSections.map((section) => (
          <button
            key={section.key}
            className={`dashboard-nav-item${section.key === active ? " active" : ""}`}
            type="button"
            onClick={() => setActive(section.key)}
          >
            {section.label}
          </button>
        ))}
      </nav>
      {message ? (
        <div className="alert success" role="status">
          <div>{message}</div>
          <button className="alert-dismiss" type="button" onClick={() => setMessage(null)} aria-label="Cerrar aviso">
            ×
          </button>
        </div>
      ) : null}
      {error ? (
        <div className="alert error" role="alert">
          <div>{error}</div>
          <button className="alert-dismiss" type="button" onClick={() => setError(null)} aria-label="Cerrar error">
            ×
          </button>
        </div>
      ) : null}
      <section className="dashboard-section" aria-live="polite">
        {activeSection?.element ?? null}
      </section>
    </div>
  );
}

export default DashboardLayout;

