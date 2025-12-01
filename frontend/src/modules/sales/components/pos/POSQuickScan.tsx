import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

type QuickScanStatus = "idle" | "processing" | "success" | "error" | "disabled";

type SubmitResult = void | string | { label?: string | null };

type POSQuickScanProps = {
  onSubmit: (code: string) => SubmitResult | Promise<SubmitResult>;
  captureTimeout?: number;
  initialEnabled?: boolean;
  onEnabledChange?: (enabled: boolean) => void;
};

const BASE_MESSAGE = "Escucha activa. Escanea un código o usa la entrada manual.";
const DISABLED_MESSAGE = "Escucha desactivada. Usa la entrada manual.";

export default function POSQuickScan({
  onSubmit,
  captureTimeout = 50,
  initialEnabled = true,
  onEnabledChange,
}: POSQuickScanProps) {
  const [manualValue, setManualValue] = useState("");
  const [status, setStatus] = useState<QuickScanStatus>(initialEnabled ? "idle" : "disabled");
  const [message, setMessage] = useState(initialEnabled ? BASE_MESSAGE : DISABLED_MESSAGE);
  const [lastCode, setLastCode] = useState<string | null>(null);
  const [lastLabel, setLastLabel] = useState<string | null>(null);
  const [listening, setListening] = useState(initialEnabled);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const statusTimerRef = useRef<number | null>(null);
  const bufferRef = useRef<string>("");
  const bufferResetRef = useRef<number | null>(null);
  const lastKeyRef = useRef<number>(0);
  const listeningRef = useRef(listening);
  const pendingCodeRef = useRef<string | null>(null);
  const processingRef = useRef(false);

  useEffect(() => {
    listeningRef.current = listening;
  }, [listening]);

  useEffect(() => {
    setStatus(listening ? "idle" : "disabled");
    setMessage(listening ? BASE_MESSAGE : DISABLED_MESSAGE);
    bufferRef.current = "";
    if (!listening && statusTimerRef.current) {
      clearTimeout(statusTimerRef.current);
      statusTimerRef.current = null;
    }
  }, [listening]);

  useEffect(
    () => () => {
      if (statusTimerRef.current) {
        clearTimeout(statusTimerRef.current);
        statusTimerRef.current = null;
      }
      if (bufferResetRef.current) {
        clearTimeout(bufferResetRef.current);
        bufferResetRef.current = null;
      }
    },
    [],
  );

  useEffect(() => {
    if (listening && inputRef.current) {
      inputRef.current.focus({ preventScroll: true });
    }
  }, [listening]);

  const scheduleReset = useCallback(() => {
    if (statusTimerRef.current) {
      clearTimeout(statusTimerRef.current);
    }
    statusTimerRef.current = window.setTimeout(() => {
      setStatus(listeningRef.current ? "idle" : "disabled");
      setMessage(listeningRef.current ? BASE_MESSAGE : DISABLED_MESSAGE);
      setLastCode(null);
      setLastLabel(null);
    }, 2200);
  }, []);

  const flushBuffer = useCallback(
    async (raw: string, options?: { force?: boolean }): Promise<boolean> => {
      const code = raw.trim();
      bufferRef.current = "";
      lastKeyRef.current = 0;
      if (!code) {
        return false;
      }

      if (!options?.force && !listeningRef.current) {
        return false;
      }

      if (processingRef.current && !options?.force) {
        pendingCodeRef.current = code;
        setMessage(`Código ${code} en cola para procesar…`);
        return true;
      }

      processingRef.current = true;
      setLastCode(code);
      setStatus("processing");
      setMessage(`Procesando ${code}…`);

      try {
        const result = await onSubmit(code);
        let label: string | undefined;
        if (typeof result === "string" && result.trim().length > 0) {
          label = result.trim();
        } else if (result && typeof result === "object") {
          const maybeLabel = (result as { label?: unknown }).label;
          if (typeof maybeLabel === "string" && maybeLabel.trim().length > 0) {
            label = maybeLabel.trim();
          }
        }

        if (label) {
          setLastLabel(label);
          setMessage(`Se agregó ${label} al carrito.`);
        } else {
          setLastLabel(null);
          setMessage(`Código ${code} agregado al carrito.`);
        }
        setStatus("success");
        scheduleReset();
        return true;
      } catch (error: unknown) {
        const fallback = "No se pudo procesar el código.";
        const errorMessage =
          error instanceof Error
            ? error.message || fallback
            : typeof error === "string"
            ? error
            : fallback;
        setStatus("error");
        setMessage(errorMessage);
        scheduleReset();
        return false;
      } finally {
        processingRef.current = false;
        const pending = pendingCodeRef.current;
        pendingCodeRef.current = null;
        if (pending && listeningRef.current) {
          void flushBuffer(pending, { force: true });
        }
      }
    },
    [onSubmit, scheduleReset],
  );

  const effectiveTimeout = useMemo(() => {
    if (!Number.isFinite(captureTimeout)) {
      return 50;
    }
    return Math.max(20, Math.trunc(captureTimeout));
  }, [captureTimeout]);

  useEffect(() => {
    if (typeof window === "undefined" || !listening) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!listeningRef.current) {
        return;
      }

      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)
      ) {
        return;
      }

      if (event.key === "Enter") {
        const buffered = bufferRef.current;
        if (bufferResetRef.current) {
          clearTimeout(bufferResetRef.current);
          bufferResetRef.current = null;
        }
        void flushBuffer(buffered);
        return;
      }

      if (event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey) {
        const now = Date.now();
        if (now - lastKeyRef.current > effectiveTimeout * 2) {
          bufferRef.current = "";
        }
        bufferRef.current += event.key;
        lastKeyRef.current = now;
        if (bufferResetRef.current) {
          clearTimeout(bufferResetRef.current);
        }
        bufferResetRef.current = window.setTimeout(() => {
          bufferRef.current = "";
          lastKeyRef.current = 0;
        }, effectiveTimeout * 8);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [effectiveTimeout, flushBuffer, listening]);

  const toggleListening = useCallback(() => {
    setListening((current) => {
      const next = !current;
      onEnabledChange?.(next);
      return next;
    });
  }, [onEnabledChange]);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const value = manualValue.trim();
      if (!value) {
        return;
      }
      const ok = await flushBuffer(value, { force: true });
      if (ok) {
        setManualValue("");
      }
    },
    [flushBuffer, manualValue],
  );

  const statusClass =
    status === "error"
      ? "pos-quick-scan__status--error"
      : status === "success"
      ? "pos-quick-scan__status--success"
      : status === "processing"
      ? "pos-quick-scan__status--processing"
      : "pos-quick-scan__status--idle";

  return (
    <section data-testid="pos-quick-scan" className="pos-quick-scan">
      <header className="pos-quick-scan__header">
        <div>
          <div className="pos-quick-scan__title">Entrada rápida (lector)</div>
          <div className="pos-quick-scan__subtitle">
            Detecta ráfagas de teclas &lt; 80&nbsp;ms provenientes de lectores de código.
          </div>
        </div>
        <label className="pos-quick-scan__toggle">
          <input
            type="checkbox"
            checked={listening}
            onChange={toggleListening}
            aria-label="Escuchar escáner global"
          />
          Escucha global
        </label>
      </header>
      <form onSubmit={handleSubmit} className="pos-quick-scan__form">
        <input
          ref={inputRef}
          value={manualValue}
          onChange={(event) => setManualValue(event.target.value)}
          placeholder="Capturar código manual"
          className="pos-quick-scan__input"
          aria-label="Código manual"
        />
        <button type="submit" className="pos-quick-scan__button">
          Aplicar
        </button>
      </form>
      <div role="status" aria-live="polite" className={`pos-quick-scan__status ${statusClass}`}>
        {message}
        {lastLabel && status !== "error" ? (
          <span className="pos-quick-scan__last-item">Último producto: {lastLabel}</span>
        ) : null}
        {!lastLabel && lastCode && status !== "error" ? (
          <span className="pos-quick-scan__last-item">Último código: {lastCode}</span>
        ) : null}
      </div>
    </section>
  );
}
