import AuditLog from "../components/AuditLog";
import TwoFactorSetup from "../components/TwoFactorSetup";
import { useSecurityModule } from "../hooks/useSecurityModule";

function SecurityPage() {
  const { token, enableTwoFactor } = useSecurityModule();

  return (
    <div className="section-grid">
      {enableTwoFactor ? (
        <TwoFactorSetup token={token} />
      ) : (
        <section className="card">
          <h2>Autenticación de dos factores</h2>
          <p className="muted-text">
            La variable <code>SOFTMOBILE_ENABLE_2FA</code> está desactivada. El módulo permanece oculto para el personal hasta
            que seguridad emita la orden de activación.
          </p>
        </section>
      )}

      <AuditLog token={token} />
    </div>
  );
}

export default SecurityPage;

