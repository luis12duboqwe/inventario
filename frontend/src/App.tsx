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
      <div className="app-shell">
        <aside className="sidebar">
          <h1>Softmobile Inventario</h1>
          <p>Cliente local para capturar movimientos y sincronizar con el servidor central.</p>
          <p className="badge">Versión tienda · Tema oscuro</p>
        </aside>
        <main className="content">
          <div className="card">
            <h2>Ingreso seguro</h2>
            <LoginForm loading={loading} error={error} onSubmit={handleLogin} />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Softmobile Inventario</h1>
        <p>Sesión activa para captura y sincronización.</p>
        <button type="button" onClick={handleLogout}>
          Cerrar sesión
        </button>
      </aside>
      <main className="content">
        <Dashboard token={token} />
      </main>
    </div>
  );
}

export default App;
