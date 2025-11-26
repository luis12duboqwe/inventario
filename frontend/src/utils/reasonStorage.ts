const STORAGE_KEY = "softmobile:last-x-reason";

function getSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function rememberReason(reason: string): void {
  const storage = getSessionStorage();
  const trimmed = reason.trim();
  if (!storage || trimmed.length < 5) {
    return;
  }
  try {
    storage.setItem(STORAGE_KEY, trimmed);
  } catch {
    // Ignoramos fallos de almacenamiento (modo incógnito, bloqueos, etc.).
  }
}

export function getStoredReason(): string | null {
  const storage = getSessionStorage();
  if (!storage) {
    return null;
  }
  try {
    const value = storage.getItem(STORAGE_KEY);
    if (!value) {
      return null;
    }
    const trimmed = value.trim();
    return trimmed.length >= 5 ? trimmed : null;
  } catch {
    return null;
  }
}

export function clearStoredReason(): void {
  const storage = getSessionStorage();
  if (!storage) {
    return;
  }
  try {
    storage.removeItem(STORAGE_KEY);
  } catch {
    // No hacemos nada si falla.
  }
}
