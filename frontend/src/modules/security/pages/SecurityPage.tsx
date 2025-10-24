import { ShieldCheck } from "lucide-react";

import AuditLog from "../components/AuditLog";
import TwoFactorSetup from "../components/TwoFactorSetup";
import ModuleHeader, { type ModuleStatus } from "../../../shared/components/ModuleHeader";
import { useSecurityModule } from "../hooks/useSecurityModule";

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
            <TwoFactorSetup token={token} />
          ) : (
            <section className="card">
              <h2>Autenticación de dos factores</h2>
              <p className="muted-text">
                La variable <code>SOFTMOBILE_ENABLE_2FA</code> está desactivada. El módulo permanece oculto para el personal
                hasta que seguridad emita la orden de activación.
              </p>
            </section>
          )}

          <AuditLog token={token} />
        </div>
      </div>
    </div>
  );
}

export default SecurityPage;

