import { useState } from "react";
import Dashboard from "./components/Dashboard";
import LoginForm from "./components/LoginForm";
import { Credentials, login } from "./api";

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("softmobile_token"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (credentials: Credentials) => {
    try {
      setLoading(true);
      setError(null);
      const response = await login(credentials);
      localStorage.setItem("softmobile_token", response.access_token);
      setToken(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("softmobile_token");
    setToken(null);
  };

  if (!token) {
    return (
      <div className="app-root login-mode">
        <main className="login-wrapper fade-in">
          <section className="card brand-card">
            <h1>Softmobile Inventario</h1>
            <p>
              Cliente corporativo para sincronizar existencias, capturar movimientos y generar respaldos con un solo
              panel.
            </p>
            <p className="badge">Versión tienda · Tema oscuro</p>
          </section>
          <section className="card login-card">
            <h2 className="accent-title">Ingreso seguro</h2>
            <LoginForm loading={loading} error={error} onSubmit={handleLogin} />
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-root">
      <header className="topbar fade-in">
        <div>
          <h1>Softmobile Inventario</h1>
          <p className="topbar-subtitle">Sesión activa para captura, reportes y sincronización multi‑tienda.</p>
        </div>
        <button type="button" onClick={handleLogout}>
          Cerrar sesión
        </button>
      </header>
      <main className="app-container fade-in">
        <Dashboard token={token} />
      </main>
    </div>
  );
}

export default App;
