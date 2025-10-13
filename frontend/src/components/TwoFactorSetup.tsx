import { FormEvent, useEffect, useState } from "react";
import {
  ActiveSession,
  TOTPSetup,
  TOTPStatus,
  activateTotp,
  disableTotp,
  getTotpStatus,
  listActiveSessions,
  revokeSession,
  setupTotp,
} from "../api";

type Props = {
  token: string;
};

function TwoFactorSetup({ token }: Props) {
  const [status, setStatus] = useState<TOTPStatus | null>(null);
  const [setup, setSetup] = useState<TOTPSetup | null>(null);
  const [code, setCode] = useState("");
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      const response = await getTotpStatus(token);
      setStatus(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible obtener el estado de 2FA");
    }
  };

  const loadSessions = async () => {
    try {
      const data = await listActiveSessions(token);
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible obtener las sesiones activas");
    }
  };

  useEffect(() => {
    loadStatus();
    loadSessions();
  }, [token]);

  const handleSetup = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await setupTotp(token);
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
    if (!code) {
      setError("Ingresa el código temporal para activar 2FA");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await activateTotp(token, code);
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
    try {
      setLoading(true);
      setError(null);
      await disableTotp(token);
      await loadStatus();
      setSetup(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible desactivar 2FA");
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (sessionId: number) => {
    try {
      setLoading(true);
      setError(null);
      await revokeSession(token, sessionId, "Revocación manual desde el panel");
      await loadSessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible revocar la sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card security-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Seguridad y doble factor</h2>
        <p className="card-subtitle">
          Habilita la verificación TOTP para cuentas administrativas y controla las sesiones activas en minutos.
        </p>
      </header>
      {error && <p className="error-text">{error}</p>}
      <div className="card-body">
        <div className="security-status">
          <p>
            Estado actual: <strong>{status?.is_active ? "Activo" : "Pendiente"}</strong>
          </p>
          {status?.activated_at && <p>Activado el: {new Date(status.activated_at).toLocaleString()}</p>}
          {status?.last_verified_at && <p>Última verificación: {new Date(status.last_verified_at).toLocaleString()}</p>}
        </div>
        <div className="security-actions">
          <button className="btn" onClick={handleSetup} disabled={loading}>
            Generar secreto TOTP
          </button>
          <button className="btn ghost" onClick={handleDisable} disabled={loading || !status?.is_active}>
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
                />
              </label>
              <button className="btn" type="submit" disabled={loading}>
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
                    <strong>{session.session_token.slice(0, 12)}</strong> — creada el {" "}
                    {new Date(session.created_at).toLocaleString()}
                  </p>
                  {session.last_used_at && <p>Último uso: {new Date(session.last_used_at).toLocaleString()}</p>}
                  {session.revoked_at && <p>Revocada el: {new Date(session.revoked_at).toLocaleString()}</p>}
                </div>
                {!session.revoked_at && (
                  <button className="btn ghost" onClick={() => handleRevoke(session.id)} disabled={loading}>
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
