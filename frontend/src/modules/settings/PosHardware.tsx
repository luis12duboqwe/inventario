import { useEffect, useMemo, useState } from "react";
import type {
  PosCashDrawerSettings,
  PosConnectorSettings,
  PosHardwareSettings,
  PosPrinterMode,
  PosPrinterSettings,
} from "@api/pos";

export type PosHardwareProps = {
  storeId: number;
  hardware: PosHardwareSettings;
  onChange: (nextHardware: PosHardwareSettings) => void;
  onTestPrinter: (printerName: string | undefined, mode: PosPrinterMode) => Promise<void>;
  onOpenDrawer: () => Promise<void>;
  onDisplayPreview: (payload: {
    headline: string;
    message: string;
    total?: number | null;
  }) => Promise<void>;
  disabled?: boolean;
  busy?: boolean;
};

const DEFAULT_PRINTER: PosPrinterSettings = {
  name: "",
  mode: "thermal",
  connector: {
    type: "usb",
    identifier: "predeterminado",
  },
  paper_width_mm: 80,
  is_default: true,
  supports_qr: false,
};

function resolvePrimaryPrinter(printers: PosPrinterSettings[]): PosPrinterSettings {
  if (printers.length === 0) {
    return { ...DEFAULT_PRINTER };
  }
  const candidate = printers.find((printer) => printer.is_default) ?? printers[0]!;
  return { ...candidate, connector: { ...candidate.connector } };
}

function PosHardware({
  storeId,
  hardware,
  onChange,
  onTestPrinter,
  onOpenDrawer,
  onDisplayPreview,
  disabled = false,
  busy = false,
}: PosHardwareProps) {
  const primaryPrinter = useMemo(
    () => resolvePrimaryPrinter(hardware.printers),
    [hardware.printers],
  );
  const [printerTesting, setPrinterTesting] = useState(false);
  const [drawerOpening, setDrawerOpening] = useState(false);
  const [displaySending, setDisplaySending] = useState(false);
  const [displayHeadline, setDisplayHeadline] = useState("Venta en mostrador");
  const [displayMessage, setDisplayMessage] = useState(
    hardware.customer_display.message_template ?? "Gracias por tu compra",
  );
  const [displayTotal, setDisplayTotal] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateHardware = (next: PosHardwareSettings) => {
    setFeedback(null);
    setError(null);
    onChange(next);
  };

  const updatePrimaryPrinter = (updates: Partial<PosPrinterSettings>) => {
    const mergedPrinter: PosPrinterSettings = {
      ...primaryPrinter,
      ...updates,
      connector: {
        ...primaryPrinter.connector,
        ...(updates.connector as PosConnectorSettings | undefined),
      },
      is_default: true,
    };
    const otherPrinters = hardware.printers.filter(
      (printer) => printer.name !== primaryPrinter.name,
    );
    updateHardware({
      ...hardware,
      printers: [mergedPrinter, ...otherPrinters],
    });
  };

  const drawerConnector: PosConnectorSettings = {
    type: hardware.cash_drawer.connector?.type ?? "usb",
    identifier: hardware.cash_drawer.connector?.identifier ?? "gaveta",
    path: hardware.cash_drawer.connector?.path ?? null,
    host: hardware.cash_drawer.connector?.host ?? null,
    port: hardware.cash_drawer.connector?.port ?? null,
  };

  const updateCashDrawer = (
    updates: Partial<Omit<PosCashDrawerSettings, "connector">> & {
      connector?: Partial<PosConnectorSettings> | null;
    },
  ) => {
    const { connector: connectorUpdates, ...rest } = updates;
    updateHardware({
      ...hardware,
      cash_drawer: {
        ...hardware.cash_drawer,
        ...rest,
        connector: {
          ...drawerConnector,
          ...(connectorUpdates ?? {}),
        },
      },
    });
  };

  const updateDisplay = (updates: Partial<PosHardwareSettings["customer_display"]>) => {
    updateHardware({
      ...hardware,
      customer_display: {
        ...hardware.customer_display,
        ...updates,
      },
    });
  };

  const handlePrinterModeChange = (mode: PosPrinterMode) => {
    updatePrimaryPrinter({ mode });
  };

  const handlePrinterConnectorChange = (
    key: keyof PosConnectorSettings,
    value: string | number,
  ) => {
    updatePrimaryPrinter({
      connector: {
        ...primaryPrinter.connector,
        [key]: value === "" ? null : value,
      },
    });
  };

  const handlePrinterTest = async () => {
    if (!primaryPrinter.name) {
      setError("Define un nombre de impresora antes de probar.");
      return;
    }
    setPrinterTesting(true);
    setFeedback(null);
    setError(null);
    try {
      await onTestPrinter(primaryPrinter.name, primaryPrinter.mode);
      setFeedback(`Impresora ${primaryPrinter.name} encola recibo de prueba.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible probar la impresora.");
    } finally {
      setPrinterTesting(false);
    }
  };

  const handleDrawerOpen = async () => {
    if (!hardware.cash_drawer.enabled) {
      setError("Activa la gaveta antes de ejecutar la prueba.");
      return;
    }
    setDrawerOpening(true);
    setFeedback(null);
    setError(null);
    try {
      await onOpenDrawer();
      setFeedback("Se solicitó la apertura de la gaveta POS.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible abrir la gaveta.");
    } finally {
      setDrawerOpening(false);
    }
  };

  const handleDisplaySend = async () => {
    if (!hardware.customer_display.enabled) {
      setError("Activa la pantalla de cliente para enviar mensajes.");
      return;
    }
    setDisplaySending(true);
    setFeedback(null);
    setError(null);
    try {
      const total = displayTotal === "" ? undefined : Number(displayTotal);
      await onDisplayPreview({
        headline: displayHeadline,
        message: displayMessage,
        total: typeof total === "number" && Number.isFinite(total) ? total : null,
      });
      setFeedback("Mensaje enviado a la pantalla de cliente.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible enviar el mensaje.");
    } finally {
      setDisplaySending(false);
    }
  };

  useEffect(() => {
    setDisplayMessage(hardware.customer_display.message_template ?? "Gracias por tu compra");
  }, [hardware.customer_display.message_template]);

  return (
    <section className="card">
      <h3>Hardware POS sucursal #{storeId}</h3>
      <p className="card-subtitle">
        Configura la impresora de recibos, la gaveta de efectivo y los avisos de pantalla del
        cliente.
      </p>
      {feedback ? <div className="alert success">{feedback}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      <div className="form-grid">
        <fieldset className="form-span">
          <legend>Impresora principal</legend>
          <label>
            Nombre
            <input
              value={primaryPrinter.name}
              onChange={(event) => updatePrimaryPrinter({ name: event.target.value })}
              disabled={disabled || busy}
            />
          </label>
          <label>
            Tipo
            <select
              value={primaryPrinter.mode}
              onChange={(event) => handlePrinterModeChange(event.target.value as PosPrinterMode)}
              disabled={disabled || busy}
            >
              <option value="thermal">Térmica</option>
              <option value="fiscal">Fiscal</option>
            </select>
          </label>
          <label>
            Conector
            <select
              value={primaryPrinter.connector.type}
              onChange={(event) =>
                handlePrinterConnectorChange(
                  "type",
                  event.target.value as PosConnectorSettings["type"],
                )
              }
              disabled={disabled || busy}
            >
              <option value="usb">USB</option>
              <option value="network">Red</option>
            </select>
          </label>
          {primaryPrinter.connector.type === "usb" ? (
            <label>
              Puerto / Ruta
              <input
                value={primaryPrinter.connector.path ?? ""}
                onChange={(event) => handlePrinterConnectorChange("path", event.target.value)}
                placeholder="/dev/usb/lp0"
                disabled={disabled || busy}
              />
            </label>
          ) : (
            <div className="form-grid form-span">
              <label>
                Host
                <input
                  value={primaryPrinter.connector.host ?? ""}
                  onChange={(event) => handlePrinterConnectorChange("host", event.target.value)}
                  placeholder="192.168.0.50"
                  disabled={disabled || busy}
                />
              </label>
              <label>
                Puerto
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={primaryPrinter.connector.port ?? 9100}
                  onChange={(event) =>
                    handlePrinterConnectorChange("port", Math.max(1, Number(event.target.value)))
                  }
                  disabled={disabled || busy}
                />
              </label>
            </div>
          )}
          <label>
            Ancho papel (mm)
            <input
              type="number"
              min={40}
              max={120}
              value={primaryPrinter.paper_width_mm ?? 80}
              onChange={(event) =>
                updatePrimaryPrinter({ paper_width_mm: Number(event.target.value) })
              }
              disabled={disabled || busy}
            />
          </label>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={handlePrinterTest}
            disabled={disabled || busy || printerTesting}
          >
            {printerTesting ? "Probando…" : "Probar impresión"}
          </button>
        </fieldset>

        <fieldset>
          <legend>Gaveta de efectivo</legend>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={hardware.cash_drawer.enabled}
              onChange={(event) => updateCashDrawer({ enabled: event.target.checked })}
              disabled={disabled || busy}
            />
            Habilitar apertura automática
          </label>
          <label>
            Identificador
            <input
              value={drawerConnector.identifier}
              onChange={(event) =>
                updateCashDrawer({ connector: { identifier: event.target.value } })
              }
              disabled={disabled || busy}
            />
          </label>
          <label>
            Conector
            <select
              value={drawerConnector.type}
              onChange={(event) =>
                updateCashDrawer({
                  connector: { type: event.target.value as PosConnectorSettings["type"] },
                })
              }
              disabled={disabled || busy}
            >
              <option value="usb">USB</option>
              <option value="network">Red</option>
            </select>
          </label>
          {drawerConnector.type === "network" ? (
            <div className="form-grid form-span">
              <label>
                Host
                <input
                  value={drawerConnector.host ?? ""}
                  onChange={(event) =>
                    updateCashDrawer({ connector: { host: event.target.value || null } })
                  }
                  placeholder="192.168.0.51"
                  disabled={disabled || busy}
                />
              </label>
              <label>
                Puerto
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={drawerConnector.port ?? 9100}
                  onChange={(event) =>
                    updateCashDrawer({
                      connector: { port: Math.max(1, Number(event.target.value)) },
                    })
                  }
                  disabled={disabled || busy}
                />
              </label>
            </div>
          ) : null}
          <label>
            Duración pulso (ms)
            <input
              type="number"
              min={50}
              max={500}
              value={hardware.cash_drawer.pulse_duration_ms}
              onChange={(event) =>
                updateCashDrawer({ pulse_duration_ms: Number(event.target.value) })
              }
              disabled={disabled || busy}
            />
          </label>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={handleDrawerOpen}
            disabled={disabled || busy || drawerOpening}
          >
            {drawerOpening ? "Abriendo…" : "Abrir gaveta"}
          </button>
        </fieldset>

        <fieldset>
          <legend>Pantalla de cliente</legend>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={hardware.customer_display.enabled}
              onChange={(event) => updateDisplay({ enabled: event.target.checked })}
              disabled={disabled || busy}
            />
            Activar mensajes en pantalla
          </label>
          <label>
            Canal
            <select
              value={hardware.customer_display.channel}
              onChange={(event) =>
                updateDisplay({
                  channel: event.target.value as PosHardwareSettings["customer_display"]["channel"],
                })
              }
              disabled={disabled || busy}
            >
              <option value="websocket">WebSocket</option>
              <option value="local">Local</option>
            </select>
          </label>
          <label>
            Encabezado
            <input
              value={displayHeadline}
              onChange={(event) => setDisplayHeadline(event.target.value)}
              disabled={disabled || busy}
            />
          </label>
          <label>
            Mensaje
            <textarea
              value={displayMessage}
              onChange={(event) => {
                setDisplayMessage(event.target.value);
                updateDisplay({ message_template: event.target.value });
              }}
              rows={3}
              disabled={disabled || busy}
            />
          </label>
          <label>
            Brillo
            <input
              type="number"
              min={10}
              max={100}
              value={hardware.customer_display.brightness}
              onChange={(event) => updateDisplay({ brightness: Number(event.target.value) })}
              disabled={disabled || busy}
            />
          </label>
          <label>
            Tema
            <select
              value={hardware.customer_display.theme}
              onChange={(event) => updateDisplay({ theme: event.target.value as "dark" | "light" })}
              disabled={disabled || busy}
            >
              <option value="dark">Oscuro</option>
              <option value="light">Claro</option>
            </select>
          </label>
          <label>
            Total mostrado
            <input
              type="number"
              min={0}
              value={displayTotal}
              onChange={(event) => setDisplayTotal(event.target.value)}
              placeholder="Opcional"
              disabled={disabled || busy}
            />
          </label>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={handleDisplaySend}
            disabled={disabled || busy || displaySending}
          >
            {displaySending ? "Enviando…" : "Probar pantalla"}
          </button>
        </fieldset>
      </div>
      <p className="muted-text">
        Guarda los cambios para sincronizar la configuración entre cajeros y clientes vinculados a
        la sucursal #{storeId}.
      </p>
    </section>
  );
}

export default PosHardware;
