import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, MonitorSmartphone, Printer, ScanLine } from "lucide-react";

import type { PosPrinterMode } from "@api/pos";
import { openPosCashDrawer, pushCustomerDisplay, testPosPrinter } from "@api/pos";
import type { Store } from "@api/inventory";

const REASON = "Diagnostico hardware POS";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
};

type ScanEntry = {
  code: string;
  length: number;
  timestamp: string;
};

type Status = {
  tone: "success" | "error" | "info";
  message: string;
};

export default function HardwareDiagnostics({ token, stores, defaultStoreId }: Props) {
  const [storeId, setStoreId] = useState<number | null>(defaultStoreId ?? stores[0]?.id ?? null);
  const [printerName, setPrinterName] = useState<string>("");
  const [printerMode, setPrinterMode] = useState<PosPrinterMode>("thermal");
  const [sampleText, setSampleText] = useState<string>("Recibo de diagnóstico Softmobile");
  const [drawerIdentifier, setDrawerIdentifier] = useState<string>("");
  const [drawerPulse, setDrawerPulse] = useState<number>(120);
  const [displayHeadline, setDisplayHeadline] = useState<string>("Pantalla de cliente");
  const [displayMessage, setDisplayMessage] = useState<string>(
    "Mensaje de prueba desde diagnóstico",
  );
  const [displayTotal, setDisplayTotal] = useState<string>("");
  const [scanInput, setScanInput] = useState<string>("");
  const [scanLog, setScanLog] = useState<ScanEntry[]>([]);
  const [busyAction, setBusyAction] = useState<"printer" | "drawer" | "display" | null>(null);
  const [status, setStatus] = useState<Status | null>(null);

  const sortedStores = useMemo(
    () => stores.slice().sort((a, b) => a.name.localeCompare(b.name)),
    [stores],
  );

  useEffect(() => {
    if (!storeId && sortedStores.length > 0) {
      setStoreId(defaultStoreId ?? sortedStores[0]?.id ?? null);
    }
  }, [defaultStoreId, sortedStores, storeId]);

  const selectedStoreName = useMemo(
    () => sortedStores.find((store) => store.id === storeId)?.name ?? "",
    [sortedStores, storeId],
  );

  const requireStore = () => {
    if (!storeId) {
      setStatus({
        tone: "error",
        message: "Selecciona una sucursal antes de ejecutar diagnósticos.",
      });
      return false;
    }
    return true;
  };

  const resetStatus = () => {
    setStatus(null);
  };

  const handlePrinterTest = async () => {
    if (!requireStore()) return;
    resetStatus();
    setBusyAction("printer");
    try {
      await testPosPrinter(
        token,
        {
          store_id: storeId!,
          ...(printerName ? { printer_name: printerName } : {}),
          mode: printerMode,
          ...(sampleText ? { sample: sampleText } : {}),
        },
        REASON,
      );
      setStatus({
        tone: "success",
        message: `Recibo de prueba enviado a ${
          printerName || "impresora principal"
        } (${selectedStoreName}).`,
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible probar la impresora.";
      setStatus({ tone: "error", message });
    } finally {
      setBusyAction(null);
    }
  };

  const handleDrawerTest = async () => {
    if (!requireStore()) return;
    resetStatus();
    setBusyAction("drawer");
    try {
      await openPosCashDrawer(
        token,
        {
          store_id: storeId!,
          ...(drawerIdentifier ? { connector_identifier: drawerIdentifier } : {}),
          pulse_duration_ms: drawerPulse,
        },
        REASON,
      );
      setStatus({
        tone: "success",
        message: "La solicitud de apertura de gaveta fue enviada correctamente.",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "No fue posible abrir la gaveta.";
      setStatus({ tone: "error", message });
    } finally {
      setBusyAction(null);
    }
  };

  const handleDisplayTest = async () => {
    if (!requireStore()) return;
    resetStatus();
    setBusyAction("display");
    try {
      const total = Number(displayTotal);
      await pushCustomerDisplay(
        token,
        {
          store_id: storeId!,
          headline: displayHeadline,
          message: displayMessage,
          ...(Number.isFinite(total) ? { total_amount: total } : {}),
        },
        REASON,
      );
      setStatus({ tone: "success", message: "Mensaje enviado a la pantalla de cliente." });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No fue posible enviar el mensaje al display.";
      setStatus({ tone: "error", message });
    } finally {
      setBusyAction(null);
    }
  };

  const handleScanCapture = () => {
    const trimmed = scanInput.trim();
    if (!trimmed) {
      setStatus({ tone: "info", message: "Escanea un código para registrar la lectura." });
      return;
    }
    const entry: ScanEntry = {
      code: trimmed,
      length: trimmed.length,
      timestamp: new Date().toLocaleTimeString(),
    };
    setScanLog((prev) => [entry, ...prev].slice(0, 5));
    setScanInput("");
    setStatus({
      tone: "success",
      message: "Lectura registrada. Verifica longitud y tiempo de captura.",
    });
  };

  return (
    <div className="card hardware-diagnostics">
      <header className="hardware-diagnostics__header">
        <div className="hardware-diagnostics__title">
          <Printer aria-hidden="true" size={18} />
          <strong>Diagnóstico de dispositivos</strong>
        </div>
        <p className="card-subtitle">
          Ejecuta pruebas rápidas sobre impresoras, gavetas, pantallas de cliente y lectores de
          código de barras sin salir del módulo de operaciones.
        </p>
      </header>

      <div className="form-grid hardware-diagnostics__form">
        <label className="form-span">
          Sucursal para pruebas
          <select
            value={storeId ?? ""}
            onChange={(event) => {
              const nextStoreId = Number(event.target.value);
              setStoreId(Number.isNaN(nextStoreId) ? null : nextStoreId);
            }}
            aria-label="Selecciona la sucursal donde se ejecutarán las pruebas"
          >
            <option value="" disabled>
              Selecciona sucursal
            </option>
            {sortedStores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Nombre impresora
          <input
            value={printerName}
            onChange={(event) => setPrinterName(event.target.value)}
            placeholder="Ticketera principal"
            autoComplete="off"
          />
        </label>
        <label>
          Modo impresora
          <select
            value={printerMode}
            onChange={(event) => setPrinterMode(event.target.value as PosPrinterMode)}
          >
            <option value="thermal">Térmica</option>
            <option value="fiscal">Fiscal</option>
          </select>
        </label>
        <label>
          Texto de muestra
          <input
            value={sampleText}
            onChange={(event) => setSampleText(event.target.value)}
            placeholder="Recibo de prueba"
          />
        </label>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={handlePrinterTest}
          disabled={busyAction === "printer"}
        >
          {busyAction === "printer" ? "Enviando…" : "Probar impresión"}
        </button>

        <label>
          Identificador gaveta
          <input
            value={drawerIdentifier}
            onChange={(event) => setDrawerIdentifier(event.target.value)}
            placeholder="Gaveta 01"
          />
        </label>
        <label>
          Pulso (ms)
          <input
            type="number"
            min={50}
            max={500}
            value={drawerPulse}
            onChange={(event) => setDrawerPulse(Number(event.target.value))}
          />
        </label>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={handleDrawerTest}
          disabled={busyAction === "drawer"}
        >
          {busyAction === "drawer" ? "Abriendo…" : "Abrir gaveta"}
        </button>

        <label>
          Encabezado display
          <input
            value={displayHeadline}
            onChange={(event) => setDisplayHeadline(event.target.value)}
            placeholder="Mostrador"
          />
        </label>
        <label>
          Mensaje display
          <input
            value={displayMessage}
            onChange={(event) => setDisplayMessage(event.target.value)}
            placeholder="Mensaje visible para cliente"
          />
        </label>
        <label>
          Total mostrado (opcional)
          <input
            type="number"
            min={0}
            value={displayTotal}
            onChange={(event) => setDisplayTotal(event.target.value)}
            placeholder="Total con impuestos"
          />
        </label>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={handleDisplayTest}
          disabled={busyAction === "display"}
        >
          {busyAction === "display" ? "Enviando…" : "Probar pantalla"}
        </button>
      </div>

      <section className="card hardware-diagnostics__scanner">
        <header className="hardware-diagnostics__scanner-header">
          <ScanLine aria-hidden="true" size={18} />
          <div>
            <strong>Prueba rápida de lector</strong>
            <p className="card-subtitle">
              Escanea tres códigos y valida longitud y tiempo de captura. El campo se limpia en cada
              registro.
            </p>
          </div>
        </header>
        <div className="form-grid hardware-diagnostics__scanner-form">
          <label className="form-span">
            Lectura de código
            <input
              value={scanInput}
              onChange={(event) => setScanInput(event.target.value)}
              placeholder="Escanea aquí"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleScanCapture();
                }
              }}
            />
          </label>
          <button type="button" className="btn" onClick={handleScanCapture}>
            Registrar lectura
          </button>
        </div>
        {scanLog.length > 0 ? (
          <ul className="data-list hardware-diagnostics__scanner-list">
            {scanLog.map((entry, index) => (
              <li key={index} className="data-list__item">
                <div>
                  <strong>{entry.code}</strong>
                  <p className="muted-text">
                    {entry.length} caracteres · {entry.timestamp}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted-text hardware-diagnostics__scanner-empty">
            Aún no hay lecturas registradas. Escanea un código de barras para validar la
            configuración del lector.
          </p>
        )}
      </section>

      {status ? (
        <div
          className={`alert ${
            status.tone === "error" ? "error" : status.tone === "success" ? "success" : "info"
          }`}
          role="status"
        >
          <div className="hardware-diagnostics__alert-content">
            {status.tone === "success" ? <CheckCircle2 aria-hidden="true" size={18} /> : null}
            {status.tone === "info" ? <MonitorSmartphone aria-hidden="true" size={18} /> : null}
            {status.tone === "error" ? <AlertTriangle aria-hidden="true" size={18} /> : null}
            <span>{status.message}</span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
