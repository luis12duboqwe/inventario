import { FormEvent, useState } from "react";
import type { Credentials } from "@api/auth";
import Button from "@components/ui/Button";
import TextField from "@components/ui/TextField";

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
    const payload: Credentials = { username, password };
    if (otp.trim()) {
      payload.otp = otp.trim();
    }
    await onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <TextField
        id="username"
        label="Usuario"
        type="text"
        required
        autoComplete="username"
        placeholder="usuario@softmobile"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />

      <TextField
        id="password"
        label="Contraseña"
        type="password"
        required
        autoComplete="current-password"
        placeholder="••••••••"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      {/* [PACK28-login-form] */}
      <TextField
        id="otp"
        label="Código TOTP"
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        autoComplete="one-time-code"
        placeholder="123456"
        value={otp}
        onChange={(event) => setOtp(event.target.value)}
      />

      {error ? <div className="alert error">{error}</div> : null}

      <Button type="submit" disabled={loading} className="auth-form__submit">
        {loading ? "Conectando…" : "Ingresar"}
      </Button>
    </form>
  );
}

export default LoginForm;
