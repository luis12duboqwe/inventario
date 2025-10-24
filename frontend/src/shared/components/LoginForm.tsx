import { FormEvent, useState } from "react";
import type { Credentials } from "../../services/api/auth";
import Button from "./ui/Button";
import TextField from "./ui/TextField";

type Props = {
  loading: boolean;
  error: string | null;
  onSubmit: (credentials: Credentials) => Promise<void> | void;
};

function LoginForm({ loading, error, onSubmit }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit({ username, password });
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

      {error ? <div className="alert error">{error}</div> : null}

      <Button type="submit" disabled={loading} className="auth-form__submit">
        {loading ? "Conectando…" : "Ingresar"}
      </Button>
    </form>
  );
}

export default LoginForm;
