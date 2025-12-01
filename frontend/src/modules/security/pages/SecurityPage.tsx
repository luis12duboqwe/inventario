import React, { Suspense } from "react";

import { ShieldCheck } from "lucide-react";

import { Loader } from "@components/ui/Loader";
import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import { useSecurityModule } from "../hooks/useSecurityModule";

const AuditLog = React.lazy(() => import("../components/AuditLog"));
const TwoFactorSetup = React.lazy(() => import("../components/TwoFactorSetup"));

function SecurityPage() {
  const { token, enableTwoFactor } = useSecurityModule();
  const status: ModuleStatus = enableTwoFactor ? "ok" : "warning";
  const statusLabel = enableTwoFactor
    ? "Controles de seguridad activos"
    : "Activa SOFTMOBILE_ENABLE_2FA para reforzar el módulo";

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<ShieldCheck aria-hidden="true" />}
        title="Seguridad"
        subtitle="Reforzamiento de accesos, doble factor y auditoría corporativa"
        status={status}
        statusLabel={statusLabel}
      />
      <div className="section-scroll">
        <div className="section-grid">
          {enableTwoFactor ? (
            <Suspense
              fallback={
                <section className="card">
                  <Loader message="Cargando autenticación de dos factores…" variant="compact" />
                </section>
              }
            >
              <TwoFactorSetup token={token} />
            </Suspense>
          ) : (
            <section className="card">
              <h2>Autenticación de dos factores</h2>
              <p className="muted-text">
                La variable <code>SOFTMOBILE_ENABLE_2FA</code> está desactivada. El módulo permanece oculto para el personal
                hasta que seguridad emita la orden de activación.
              </p>
            </section>
          )}

          <Suspense
            fallback={
              <section className="card">
                <Loader message="Cargando bitácora de auditoría…" variant="compact" />
              </section>
            }
          >
            <AuditLog token={token} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

export default SecurityPage;

