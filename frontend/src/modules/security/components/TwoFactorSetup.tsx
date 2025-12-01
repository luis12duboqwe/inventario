import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  type ActiveSession,
  type TOTPSetup,
  type TOTPStatus,
  activateTotp,
  disableTotp,
  getTotpStatus,
  listActiveSessions,
  revokeSession,
  setupTotp,
} from "@api/security";

type Props = {
  token: string;
};

function TwoFactorSetup({ token }: Props) {
  const [status, setStatus] = useState<TOTPStatus | null>(null);
  const [setup, setSetup] = useState<TOTPSetup | null>(null);
  const [code, setCode] = useState("");
  const [reason, setReason] = useState("");
  const [reauthPassword, setReauthPassword] = useState("");
  const [reauthOtp, setReauthOtp] = useState("");
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFeatureEnabled, setIsFeatureEnabled] = useState(true);

  const ensureReason = (): string | null => {
    const trimmed = reason.trim();
    if (trimmed.length < 5) {
      setError("Proporciona un motivo corporativo de al menos 5 caracteres.");
      return null;
    }
    return trimmed;
  };

  const loadStatus = useCallback(async () => {
    try {
      const response = await getTotpStatus(token);
      setIsFeatureEnabled(true);
      setStatus(response);
    } catch (err) {
      if (err instanceof Error && err.message.includes("Funcionalidad no disponible")) {
        setIsFeatureEnabled(false);
        setStatus(null);
        setSetup(null);
        setError(null);
        return;
      }
      setError(err instanceof Error ? err.message : "No fue posible obtener el estado de 2FA");
    }
  }, [token]);

  const loadSessions = useCallback(async () => {
    try {
      const data = await listActiveSessions(token);
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible obtener las sesiones activas");
    }
  }, [token]);

  useEffect(() => {
    void loadStatus();
    void loadSessions();
  }, [loadStatus, loadSessions]);

  const handleSetup = async () => {
    if (!isFeatureEnabled) {
      setError("La verificación en dos pasos está deshabilitada por configuración corporativa.");
      return;
    }
    const validReason = ensureReason();
    if (!validReason) {
      return;
    }
    if (!reauthPassword.trim()) {
      setError("Confirma tu contraseña para continuar.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await setupTotp(token, validReason, {
        password: reauthPassword,
        ...(reauthOtp ? { otp: reauthOtp } : {}),
      });
      setSetup(response);
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible generar el secreto TOTP");
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (event: FormEvent) => {
    event.preventDefault();
    if (!isFeatureEnabled) {
      setError("La verificación en dos pasos está deshabilitada por configuración corporativa.");
      return;
    }
    if (!code) {
      setError("Ingresa el código temporal para activar 2FA");
      return;
    }
    const validReason = ensureReason();
    if (!validReason) {
      return;
    }
    if (!reauthPassword.trim()) {
      setError("Confirma tu contraseña para continuar.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await activateTotp(token, code, validReason, {
        password: reauthPassword,
        ...(reauthOtp ? { otp: reauthOtp } : {}),
      });
      setStatus(response);
      setSetup(null);
      setCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Código inválido");
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    if (!isFeatureEnabled) {
      setError("La verificación en dos pasos está deshabilitada por configuración corporativa.");
      return;
    }
    const validReason = ensureReason();
    if (!validReason) {
      return;
    }
    if (!reauthPassword.trim()) {
      setError("Confirma tu contraseña para continuar.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      await disableTotp(token, validReason, {
        password: reauthPassword,
        ...(reauthOtp ? { otp: reauthOtp } : {}),
      });
      await loadStatus();
      setSetup(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible desactivar 2FA");
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (sessionId: number) => {
    if (!isFeatureEnabled) {
      setError("La verificación en dos pasos está deshabilitada por configuración corporativa.");
      return;
    }
    const validReason = ensureReason();
    if (!validReason) {
      return;
    }
    if (!reauthPassword.trim()) {
      setError("Confirma tu contraseña para continuar.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      await revokeSession(token, sessionId, `${validReason} — revocación de sesión`, {
        password: reauthPassword,
        ...(reauthOtp ? { otp: reauthOtp } : {}),
      });
      await loadSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible revocar la sesión");
    } finally {
      setLoading(false);
    }
  };

  const actionsDisabled = loading || !isFeatureEnabled;

  return (
    <section className="card security-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Seguridad y doble factor</h2>
        <p className="card-subtitle">
          Habilita la verificación TOTP para cuentas administrativas y controla las sesiones activas
          en minutos.
        </p>
      </header>
      {!isFeatureEnabled && (
        <p className="muted-text" role="status">
          La verificación en dos pasos está deshabilitada por configuración corporativa (flag
          SOFTMOBILE_ENABLE_2FA).
        </p>
      )}
      {error && <p className="error-text">{error}</p>}
      <div className="card-body">
        <div className="security-status">
          <p>
            Estado actual: <strong>{status?.is_active ? "Activo" : "Pendiente"}</strong>
          </p>
          {status?.activated_at && (
            <p>Activado el: {new Date(status.activated_at).toLocaleString()}</p>
          )}
          {status?.last_verified_at && (
            <p>Última verificación: {new Date(status.last_verified_at).toLocaleString()}</p>
          )}
        </div>
        <div className="reason-field">
          <label>
            <span>Motivo corporativo</span>
            <input
              type="text"
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                if (error && event.target.value.trim().length >= 5) {
                  setError(null);
                }
              }}
              placeholder="Describe por qué modificas la configuración de 2FA"
              minLength={5}
              disabled={actionsDisabled}
              required
            />
          </label>
          <p className="muted-text">
            Se reutilizará para activar, desactivar o revocar sesiones. Mínimo 5 caracteres.
          </p>
        </div>
        <div className="reauth-grid">
          <label>
            <span>Confirma tu contraseña</span>
            <input
              type="password"
              value={reauthPassword}
              onChange={(event) => setReauthPassword(event.target.value)}
              placeholder="Ingresa tu contraseña actual"
              minLength={8}
              autoComplete="current-password"
              disabled={actionsDisabled}
              required
            />
          </label>
          <label>
            <span>Código TOTP para confirmar</span>
            <input
              type="text"
              value={reauthOtp}
              onChange={(event) => setReauthOtp(event.target.value)}
              placeholder="Solo si tienes 2FA activo"
              pattern="\\d{6}"
              inputMode="numeric"
              maxLength={6}
              disabled={actionsDisabled}
            />
          </label>
          <p className="muted-text">
            Requerimos una reautenticación rápida para cambios sensibles o revocación de sesiones.
          </p>
        </div>
        <div className="security-actions">
          <button className="btn btn--primary" onClick={handleSetup} disabled={actionsDisabled}>
            Generar secreto TOTP
          </button>
          <button
            className="btn btn--ghost"
            onClick={handleDisable}
            disabled={actionsDisabled || !status?.is_active}
          >
            Desactivar 2FA
          </button>
        </div>
        {setup && (
          <div className="totp-setup">
            <p>Escanea el código con Google Authenticator o ingresa el secreto manualmente:</p>
            <code className="code-block">{setup.secret}</code>
            <a className="link" href={setup.otpauth_url} target="_blank" rel="noreferrer">
              Abrir enlace OTP
            </a>
            <form className="totp-form" onSubmit={handleActivate}>
              <label>
                <span>Código de 6 dígitos</span>
                <input
                  type="text"
                  value={code}
                  maxLength={6}
                  pattern="\\d{6}"
                  onChange={(event) => setCode(event.target.value)}
                  disabled={actionsDisabled}
                />
              </label>
              <button className="btn btn--primary" type="submit" disabled={actionsDisabled}>
                Activar 2FA
              </button>
            </form>
          </div>
        )}
      </div>
      <footer className="card-footer">
        <h3 className="accent-title">Sesiones activas</h3>
        {sessions.length === 0 ? (
          <p>No hay sesiones activas registradas.</p>
        ) : (
          <ul className="session-list">
            {sessions.map((session) => (
              <li key={session.id} className="session-item">
                <div>
                  <p>
                    <strong>{session.session_token.slice(0, 12)}</strong> — creada el{" "}
                    {new Date(session.created_at).toLocaleString()}
                  </p>
                  {session.last_used_at && (
                    <p>Último uso: {new Date(session.last_used_at).toLocaleString()}</p>
                  )}
                  {session.revoked_at && (
                    <p>Revocada el: {new Date(session.revoked_at).toLocaleString()}</p>
                  )}
                </div>
                {!session.revoked_at && (
                  <button
                    className="btn btn--ghost"
                    onClick={() => handleRevoke(session.id)}
                    disabled={actionsDisabled}
                  >
                    Revocar
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </footer>
    </section>
  );
}

export default TwoFactorSetup;
