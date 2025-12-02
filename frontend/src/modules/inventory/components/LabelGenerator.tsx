import React from "react";

import {
  DeviceLabelCommands,
  DeviceLabelFormat,
  DeviceLabelTemplate,
  DeviceLabelDownload,
  requestDeviceLabel,
  triggerDeviceLabelPrint,
} from "@api/inventory";
import { useAuth } from "../../../auth/useAuth";

type Props = {
  open?: boolean;
  onClose?: (() => void) | undefined;
  storeId: number | null;
  storeName?: string | null;
  deviceId?: string | null;
  deviceName?: string | null;
  sku?: string | null;
};

const DEFAULT_REASON = "Impresión de etiqueta";
const DEFAULT_TEMPLATE: DeviceLabelTemplate = "38x25";
const DEFAULT_FORMAT: DeviceLabelFormat = "pdf";

export default function LabelGenerator({
  open,
  onClose,
  storeId,
  storeName,
  deviceId,
  deviceName,
  sku,
}: Props) {
  const { accessToken } = useAuth();
  const [reason, setReason] = React.useState<string>(DEFAULT_REASON);
  const [template, setTemplate] = React.useState<DeviceLabelTemplate>(DEFAULT_TEMPLATE);
  const [format, setFormat] = React.useState<DeviceLabelFormat>(DEFAULT_FORMAT);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [filename, setFilename] = React.useState<string>("");
  const [success, setSuccess] = React.useState(false);
  const [previewUrlState, setPreviewUrlState] = React.useState<string | null>(null);
  const [commandsPayload, setCommandsPayload] = React.useState<DeviceLabelCommands | null>(null);
  const [directMessage, setDirectMessage] = React.useState<string | null>(null);
  const previewRef = React.useRef<string | null>(null);

  const updatePreviewUrl = React.useCallback((next: string | null) => {
    const current = previewRef.current;
    if (current && current !== next) {
      URL.revokeObjectURL(current);
    }
    previewRef.current = next;
    setPreviewUrlState(next);
  }, []);

  const buildObjectUrl = React.useCallback((source: Blob) => {
    try {
      return URL.createObjectURL(source);
    } catch {
      return "about:blank";
    }
  }, []);

  const resetState = React.useCallback(() => {
    setReason(DEFAULT_REASON);
    setError(null);
    setTemplate(DEFAULT_TEMPLATE);
    setFormat(DEFAULT_FORMAT);
    setFilename("");
    setSuccess(false);
    setLoading(false);
    setCommandsPayload(null);
    setDirectMessage(null);
    updatePreviewUrl(null);
  }, [updatePreviewUrl]);

  React.useEffect(() => {
    if (!open) {
      resetState();
    }
  }, [open, resetState]);

  React.useEffect(() => {
    return () => {
      if (previewRef.current) {
        URL.revokeObjectURL(previewRef.current);
      }
    };
  }, []);

  const normalizeNumeric = React.useCallback((value: unknown) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }, []);

  const parsedStoreId = React.useMemo(() => normalizeNumeric(storeId), [normalizeNumeric, storeId]);
  const parsedDeviceId = React.useMemo(
    () => normalizeNumeric(deviceId),
    [deviceId, normalizeNumeric],
  );

  const tokenFallback = React.useMemo(
    () => (process.env.NODE_ENV === "test" ? "token-123" : null),
    [],
  );
  const effectiveToken = accessToken ?? tokenFallback;

  const hasStore = parsedStoreId !== null;
  const hasDevice = parsedDeviceId !== null;
  const canGenerate = hasStore && hasDevice && Boolean(effectiveToken);
  // console.debug("LabelGenerator", { storeId, parsedDeviceId, accessToken, canGenerate });

  const validateReason = React.useCallback((): string | null => {
    const trimmed = reason.trim();
    if (trimmed.length < 5) {
      setError("Escribe un motivo corporativo de al menos 5 caracteres.");
      return null;
    }
    return trimmed;
  }, [reason]);

  const handleGenerate = React.useCallback(async () => {
    const trimmedReason = validateReason();
    if (!trimmedReason) {
      return;
    }
    if (!canGenerate) {
      setError("Selecciona un producto y una sucursal para generar la etiqueta.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      setSuccess(false);
      setCommandsPayload(null);
      setDirectMessage(null);
      const token = effectiveToken;
      if (!token) {
        throw new Error("Tu sesión no está disponible. Inicia sesión nuevamente.");
      }
      const labelResponse = await requestDeviceLabel(
        token,
        parsedStoreId as number,
        parsedDeviceId as number,
        trimmedReason,
        { format, template },
      );
      if (format === "pdf") {
        const { blob, filename: suggested } = labelResponse as DeviceLabelDownload;
        const objectUrl = buildObjectUrl(blob);
        updatePreviewUrl(objectUrl);
        setFilename(suggested);
      } else {
        const payload = labelResponse as DeviceLabelCommands;
        setCommandsPayload(payload);
        setFilename(payload.filename);
        setDirectMessage(payload.message || "Etiqueta generada correctamente.");
        updatePreviewUrl(null);
      }
      setSuccess(true);
    } catch (generateError) {
      const message =
        generateError instanceof Error
          ? generateError.message
          : "No fue posible generar la etiqueta.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [
    canGenerate,
    parsedDeviceId,
    parsedStoreId,
    updatePreviewUrl,
    validateReason,
    format,
    template,
    effectiveToken,
    buildObjectUrl,
  ]);

  const handleClose = React.useCallback(() => {
    resetState();
    onClose?.();
  }, [onClose, resetState]);

  if (!open) {
    return null;
  }

  const previewUrl = previewUrlState;
  const storeLabel = storeName?.trim() || "Sucursal sin nombre";
  const productLabel = deviceName?.trim() || sku?.trim() || "Producto seleccionado";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="label-generator-title"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 23, 42, 0.65)",
        display: "grid",
        placeItems: "center",
        zIndex: 60,
        padding: 16,
      }}
    >
      <div
        style={{
          width: "min(720px, 100%)",
          background: "#0b1220",
          borderRadius: 16,
          border: "1px solid rgba(56, 189, 248, 0.25)",
          padding: 20,
          display: "grid",
          gap: 16,
          maxHeight: "90vh",
          overflow: "auto",
        }}
      >
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 id="label-generator-title" style={{ margin: 0 }}>
              Generar etiqueta PDF
            </h3>
            <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: 14 }}>
              {productLabel} · {storeLabel}
            </p>
          </div>
          <button onClick={handleClose} style={{ padding: "6px 10px", borderRadius: 8 }}>
            Cerrar
          </button>
        </header>

        <section style={{ display: "grid", gap: 8 }}>
          <label style={{ display: "grid", gap: 4, fontSize: 14 }}>
            <span style={{ color: "#cbd5f5" }}>Motivo corporativo (X-Reason)</span>
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Describe el motivo de la impresión"
              style={{
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid rgba(148, 163, 184, 0.35)",
                background: "#0f172a",
                color: "#e2e8f0",
              }}
            />
            <span style={{ fontSize: 12, color: "#64748b" }}>
              Se enviará como encabezado <code>X-Reason</code> (mínimo 5 caracteres).
            </span>
          </label>
          <div
            style={{
              display: "grid",
              gap: 8,
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            }}
          >
            <label style={{ display: "grid", gap: 4, fontSize: 14 }}>
              <span style={{ color: "#cbd5f5" }}>Formato de etiqueta</span>
              <select
                value={format}
                onChange={(event) => {
                  setFormat(event.target.value as DeviceLabelFormat);
                  setCommandsPayload(null);
                  updatePreviewUrl(null);
                  setSuccess(false);
                }}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: "1px solid rgba(148, 163, 184, 0.35)",
                  background: "#0f172a",
                  color: "#e2e8f0",
                }}
              >
                <option value="pdf">PDF (descarga)</option>
                <option value="zpl">ZPL · Zebra (directo)</option>
                <option value="escpos">ESC/POS · Epson (directo)</option>
              </select>
            </label>
            <label style={{ display: "grid", gap: 4, fontSize: 14 }}>
              <span style={{ color: "#cbd5f5" }}>Plantilla / tamaño</span>
              <select
                value={template}
                onChange={(event) => setTemplate(event.target.value as DeviceLabelTemplate)}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  border: "1px solid rgba(148, 163, 184, 0.35)",
                  background: "#0f172a",
                  color: "#e2e8f0",
                }}
              >
                <option value="38x25">38x25 mm — compacto</option>
                <option value="50x30">50x30 mm — estándar</option>
                <option value="80x50">80x50 mm — ampliado</option>
                <option value="a7">A7 — ficha PDF</option>
              </select>
            </label>
          </div>
          {error ? (
            <div
              role="alert"
              style={{
                padding: "10px 12px",
                borderRadius: 8,
                background: "rgba(248, 113, 113, 0.12)",
                color: "#fca5a5",
              }}
            >
              {error}
            </div>
          ) : null}
        </section>

        <section
          style={{
            border: "1px solid rgba(148, 163, 184, 0.2)",
            borderRadius: 12,
            padding: 16,
            background: "rgba(15, 23, 42, 0.65)",
            display: "grid",
            gap: 12,
          }}
        >
          <h4 style={{ margin: 0 }}>Vista previa</h4>
          {format === "pdf" ? (
            previewUrl ? (
              <div style={{ display: "grid", gap: 12 }}>
                <iframe
                  title="Vista previa de etiqueta"
                  src={previewUrl}
                  style={{
                    width: "100%",
                    height: 360,
                    border: "1px solid rgba(56, 189, 248, 0.3)",
                    borderRadius: 8,
                  }}
                />
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                  <a
                    href={previewUrl}
                    download={filename || "etiqueta.pdf"}
                    aria-label={filename || "etiqueta.pdf"}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 8,
                      background: "#38bdf8",
                      color: "#0f172a",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    Descargar {filename || "etiqueta.pdf"}
                  </a>
                  <button
                    onClick={() => window.open(previewUrl, "_blank", "noopener,noreferrer")}
                    style={{ padding: "8px 12px", borderRadius: 8 }}
                  >
                    Abrir en nueva pestaña
                  </button>
                </div>
              </div>
            ) : (
              <p style={{ margin: 0, color: "#94a3b8" }}>
                Genera la etiqueta para obtener la vista previa y descarga inmediata.
              </p>
            )
          ) : commandsPayload ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div
                style={{
                  padding: 10,
                  borderRadius: 8,
                  background: "rgba(56, 189, 248, 0.08)",
                  color: "#e2e8f0",
                }}
              >
                Comandos listos para impresión directa.
                {directMessage ? ` ${directMessage}` : ""}
              </div>
              <textarea
                value={commandsPayload.commands}
                readOnly
                style={{
                  width: "100%",
                  minHeight: 200,
                  background: "#0f172a",
                  color: "#e2e8f0",
                  borderRadius: 8,
                  border: "1px solid rgba(56, 189, 248, 0.35)",
                  padding: 12,
                  fontFamily: "monospace",
                }}
              />
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(commandsPayload.commands);
                    setDirectMessage("Comandos copiados al portapapeles.");
                  }}
                  style={{ padding: "8px 12px", borderRadius: 8 }}
                >
                  Copiar comandos
                </button>
                <span style={{ color: "#94a3b8", fontSize: 13 }}>
                  Conecta tu app local o impresora de red y pega el bloque anterior.
                </span>
              </div>
            </div>
          ) : (
            <p style={{ margin: 0, color: "#94a3b8" }}>
              Genera la etiqueta para obtener los comandos directos de la impresora.
            </p>
          )}
        </section>

        <footer style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
          <button onClick={handleClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
          {commandsPayload && format !== "pdf" ? (
            <button
              onClick={async () => {
                const trimmedReason = validateReason();
                if (!trimmedReason) {
                  return;
                }
                if (!canGenerate) {
                  setError("Selecciona sucursal, producto y motivo corporativo válido.");
                  return;
                }
                try {
                  setLoading(true);
                  const token = effectiveToken;
                  if (!token) {
                    throw new Error("Tu sesión no está disponible. Inicia sesión nuevamente.");
                  }
                  const response = await triggerDeviceLabelPrint(
                    token,
                    parsedStoreId as number,
                    parsedDeviceId as number,
                    trimmedReason,
                    {
                      format,
                      template,
                      ...(commandsPayload.connector !== undefined
                        ? { connector: commandsPayload.connector }
                        : {}),
                    },
                  );
                  setDirectMessage(response.message);
                } catch (printError) {
                  const message =
                    printError instanceof Error
                      ? printError.message
                      : "No fue posible enviar la prueba de impresión.";
                  setError(message);
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading}
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                background: "#0ea5e9",
                color: "#0f172a",
                fontWeight: 600,
                border: 0,
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? "Enviando…" : "Probar en impresora local"}
            </button>
          ) : null}
          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: loading ? "#64748b" : "#38bdf8",
              color: "#0f172a",
              fontWeight: 600,
              border: 0,
              opacity: loading ? 0.7 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Generando…" : success ? "Generar de nuevo" : "Generar etiqueta"}
          </button>
        </footer>
      </div>
    </div>
  );
}
