import { FormEvent, useCallback, useMemo, useState } from "react";

import Button from "./ui/Button";
import TextField from "./ui/TextField";

export type BootstrapFormValues = {
  username: string;
  password: string;
  fullName?: string;
  telefono?: string;
};

type Props = {
  loading: boolean;
  error: string | null;
  successMessage: string | null;
  onSubmit: (values: BootstrapFormValues) => Promise<void> | void;
};

type FormState = {
  username: string;
  fullName: string;
  telefono: string;
  password: string;
  confirmPassword: string;
};

const defaultState: FormState = {
  username: "",
  fullName: "",
  telefono: "",
  password: "",
  confirmPassword: "",
};

function normalizePayload(state: FormState): BootstrapFormValues {
  const username = state.username.trim();
  const fullName = state.fullName.trim();
  const telefono = state.telefono.trim();

  const payload: BootstrapFormValues = {
    username,
    password: state.password,
  };

  if (fullName) {
    payload.fullName = fullName;
  }

  if (telefono) {
    payload.telefono = telefono;
  }

  return payload;
}

function BootstrapForm({ loading, error, successMessage, onSubmit }: Props) {
  const [formState, setFormState] = useState<FormState>(defaultState);
  const [validationError, setValidationError] = useState<string | null>(null);

  const passwordMismatch = useMemo(() => {
    return formState.confirmPassword.length > 0 && formState.password !== formState.confirmPassword;
  }, [formState.password, formState.confirmPassword]);

  // Limpiar errores de forma reactiva durante la edición, sin usar efectos

  const handleChange = useCallback((field: keyof FormState, value: string) => {
    setFormState((current) => {
      const next = { ...current, [field]: value } as FormState;
      // Limpia error de correo obligatorio al escribir un valor válido
      if (
        field === "username" &&
        validationError === "El correo corporativo es obligatorio." &&
        next.username.trim()
      ) {
        // microtarea opcional para garantizar fuera del render
        Promise.resolve().then(() => setValidationError(null));
      }
      // Limpia error de contraseñas si deja de existir el desajuste
      if (field === "password" || field === "confirmPassword") {
        const mismatch =
          next.confirmPassword.length > 0 && next.password !== next.confirmPassword;
        if (!mismatch && validationError === "Las contraseñas no coinciden.") {
          Promise.resolve().then(() => setValidationError(null));
        }
      }
      return next;
    });
  }, [validationError]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedUsername = formState.username.trim();
      if (!trimmedUsername) {
        setValidationError("El correo corporativo es obligatorio.");
        return;
      }
      if (formState.password.length < 8) {
        setValidationError("La contraseña debe tener al menos 8 caracteres.");
        return;
      }
      if (formState.password !== formState.confirmPassword) {
        setValidationError("Las contraseñas no coinciden.");
        return;
      }
      setValidationError(null);
      await onSubmit(normalizePayload(formState));
    },
    [formState, onSubmit],
  );

  const helperText = useMemo(() => {
    if (!formState.password) {
      return "Utiliza una contraseña robusta con números y caracteres especiales.";
    }
    if (passwordMismatch) {
      return "Confirma que ambos campos de contraseña coinciden.";
    }
    return null;
  }, [formState.password, passwordMismatch]);

  const bootstrapHint = useMemo(() => {
    const base: string[] = ["Esta cuenta tendrá permisos de administración completa."];
    base.push("Guarda tus credenciales en un gestor seguro tras completar el registro.");
    return base.join(" ");
  }, []);

  return (
    <form onSubmit={handleSubmit} className="auth-form" noValidate>
      <TextField
        id="bootstrap-username"
        label="Correo corporativo"
        type="email"
        required
        autoComplete="username"
        placeholder="admin@softmobile"
        value={formState.username}
        onChange={(event) => handleChange("username", event.target.value)}
      />

      <TextField
        id="bootstrap-fullname"
        label="Nombre completo"
        type="text"
        autoComplete="name"
        placeholder="Administradora General"
        value={formState.fullName}
        onChange={(event) => handleChange("fullName", event.target.value)}
      />

      <TextField
        id="bootstrap-phone"
        label="Teléfono de contacto"
        type="tel"
        autoComplete="tel"
        placeholder="+34 600 000 000"
        value={formState.telefono}
        onChange={(event) => handleChange("telefono", event.target.value)}
      />

      <TextField
        id="bootstrap-password"
        label="Contraseña"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
        placeholder="••••••••"
        value={formState.password}
        onChange={(event) => handleChange("password", event.target.value)}
        {...(helperText ? { helperText } : { helperText: bootstrapHint })}
      />

      <TextField
        id="bootstrap-confirm"
        label="Confirmar contraseña"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
        placeholder="••••••••"
        value={formState.confirmPassword}
        onChange={(event) => handleChange("confirmPassword", event.target.value)}
        {...(passwordMismatch ? { error: "Las contraseñas no coinciden." } : {})}
      />

      {validationError ? <div className="alert error">{validationError}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      {successMessage ? <div className="alert success">{successMessage}</div> : null}

      <Button type="submit" disabled={loading} className="auth-form__submit">
        {loading ? "Creando cuenta…" : "Registrar cuenta"}
      </Button>
    </form>
  );
}

export default BootstrapForm;
