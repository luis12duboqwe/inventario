import { useState, useCallback } from "react";

export type ToastVariant = "success" | "error" | "info" | "warning";

export type ToastMessage = {
  id: number;
  message: string;
  variant: ToastVariant;
};

export function useUIState() {
  const [compactMode, setCompactModeState] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem("softmobile_compact_mode") === "1";
  });
  const [globalSearchTerm, setGlobalSearchTerm] = useState<string>("");
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [networkAlert, setNetworkAlert] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const persistCompactMode = (value: boolean) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("softmobile_compact_mode", value ? "1" : "0");
    }
  };

  const setCompactMode = useCallback((value: boolean) => {
    setCompactModeState(value);
    persistCompactMode(value);
  }, []);

  const toggleCompactMode = useCallback(() => {
    setCompactModeState((current) => {
      const next = !current;
      persistCompactMode(next);
      return next;
    });
  }, []);

  const pushToast = useCallback((toast: Omit<ToastMessage, "id">) => {
    const id = Date.now() + Math.round(Math.random() * 1000);
    setToasts((current) => [...current, { id, ...toast }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((entry) => entry.id !== id));
    }, 4500);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const dismissNetworkAlert = useCallback(() => {
    setNetworkAlert(null);
  }, []);

  const friendlyErrorMessage = useCallback((msg: string) => {
    if (!msg) {
      return "Ocurrió un error inesperado";
    }
    if (msg.toLowerCase().includes("failed to fetch")) {
      return "No fue posible conectar con el servicio Softmobile. Verifica tu red e inténtalo nuevamente.";
    }
    return msg;
  }, []);

  return {
    compactMode,
    setCompactMode,
    toggleCompactMode,
    globalSearchTerm,
    setGlobalSearchTerm,
    toasts,
    pushToast,
    dismissToast,
    networkAlert,
    setNetworkAlert,
    dismissNetworkAlert,
    loading,
    setLoading,
    message,
    setMessage,
    error,
    setError,
    friendlyErrorMessage,
  };
}
