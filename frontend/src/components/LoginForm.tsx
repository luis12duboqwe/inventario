import { FormEvent, useState } from "react";
import { Credentials } from "../api";

type Props = {
  loading: boolean;
  error: string | null;
  onSubmit: (credentials: Credentials) => Promise<void> | void;
};

function LoginForm({ loading, error, onSubmit }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit({ username, password, otp: otp.trim() || undefined });
  };

  return (
    <form onSubmit={handleSubmit} className="form-grid">
      <label htmlFor="username">Usuario</label>
      <input
        id="username"
        type="text"
        required
        autoComplete="username"
        placeholder="usuario@softmobile"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />

      <label htmlFor="password">Contraseña</label>
      <input
        id="password"
        type="password"
        required
        autoComplete="current-password"
        placeholder="••••••••"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      <label htmlFor="otp">Código 2FA (si aplica)</label>
      <input
        id="otp"
        type="text"
        inputMode="numeric"
        pattern="\d{6}"
        autoComplete="one-time-code"
        placeholder="123456"
        value={otp}
        onChange={(event) => setOtp(event.target.value)}
      />

      {error ? <div className="alert error">{error}</div> : null}

      <button type="submit" disabled={loading} className="submit-button">
        {loading ? "Conectando…" : "Ingresar"}
      </button>
    </form>
  );
}

export default LoginForm;
