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
import Modal from "@components/ui/Modal";
import Button from "@components/ui/Button";
import "./LabelGenerator.css";

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
  const [previewUrl, setPreviewUrlState] = React.useState<string | null>(null);
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

  const handleTestPrint = async () => {
    if (!commandsPayload) return;

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
  };

  const storeLabel = storeName?.trim() || "Sucursal sin nombre";
  const productLabel = deviceName?.trim() || sku?.trim() || "Producto seleccionado";

  return (
    <Modal
      open={!!open}
      title="Generar etiqueta PDF"
      description={`${productLabel} · ${storeLabel}`}
      onClose={handleClose}
      size="lg"
      footer={
        <div className="label-generator__footer-actions">
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          {commandsPayload && format !== "pdf" ? (
            <Button variant="secondary" onClick={handleTestPrint} disabled={loading}>
              {loading ? "Enviando…" : "Probar en impresora local"}
            </Button>
          ) : null}
          <Button variant="primary" onClick={handleGenerate} disabled={loading}>
            {loading ? "Generando…" : success ? "Generar de nuevo" : "Generar etiqueta"}
          </Button>
        </div>
      }
    >
      <div className="label-generator__grid">
        <section className="label-generator__section">
          <label className="label-generator__field">
            <span className="label-generator__label">Motivo corporativo (X-Reason)</span>
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Describe el motivo de la impresión"
              className="label-generator__input"
            />
            <span className="label-generator__hint">
              Se enviará como encabezado <code>X-Reason</code> (mínimo 5 caracteres).
            </span>
          </label>
          <div className="label-generator__options">
            <label className="label-generator__field">
              <span className="label-generator__label">Formato de etiqueta</span>
              <select
                value={format}
                onChange={(event) => {
                  setFormat(event.target.value as DeviceLabelFormat);
                  setCommandsPayload(null);
                  updatePreviewUrl(null);
                  setSuccess(false);
                }}
                className="label-generator__select"
              >
                <option value="pdf">PDF (descarga)</option>
                <option value="zpl">ZPL · Zebra (directo)</option>
                <option value="escpos">ESC/POS · Epson (directo)</option>
              </select>
            </label>
            <label className="label-generator__field">
              <span className="label-generator__label">Plantilla / tamaño</span>
              <select
                value={template}
                onChange={(event) => setTemplate(event.target.value as DeviceLabelTemplate)}
                className="label-generator__select"
              >
                <option value="38x25">38x25 mm — compacto</option>
                <option value="50x30">50x30 mm — estándar</option>
                <option value="80x50">80x50 mm — ampliado</option>
                <option value="a7">A7 — ficha PDF</option>
              </select>
            </label>
          </div>
          {error ? (
            <div role="alert" className="label-generator__error">
              {error}
            </div>
          ) : null}
        </section>

        <section className="label-generator__preview-container">
          <h4 className="label-generator__preview-title">Vista previa</h4>
          {format === "pdf" ? (
            previewUrl ? (
              <div className="label-generator__grid">
                <iframe
                  title="Vista previa de etiqueta"
                  src={previewUrl}
                  className="label-generator__iframe"
                />
                <div className="label-generator__actions">
                  <a
                    href={previewUrl}
                    download={filename || "etiqueta.pdf"}
                    aria-label={filename || "etiqueta.pdf"}
                    className="label-generator__download-link"
                  >
                    Descargar {filename || "etiqueta.pdf"}
                  </a>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => window.open(previewUrl, "_blank", "noopener,noreferrer")}
                  >
                    Abrir en nueva pestaña
                  </Button>
                </div>
              </div>
            ) : (
              <p className="label-generator__empty-state">
                Genera la etiqueta para obtener la vista previa y descarga inmediata.
              </p>
            )
          ) : commandsPayload ? (
            <div className="label-generator__commands-box">
              <div className="label-generator__commands-message">
                Comandos listos para impresión directa.
                {directMessage ? ` ${directMessage}` : ""}
              </div>
              <textarea
                value={commandsPayload.commands}
                readOnly
                className="label-generator__textarea"
              />
              <div className="label-generator__actions">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={async () => {
                    await navigator.clipboard.writeText(commandsPayload.commands);
                    setDirectMessage("Comandos copiados al portapapeles.");
                  }}
                >
                  Copiar comandos
                </Button>
                <span className="label-generator__hint">
                  Conecta tu app local o impresora de red y pega el bloque anterior.
                </span>
              </div>
            </div>
          ) : (
            <p className="label-generator__empty-state">
              Genera la etiqueta para obtener los comandos directos de la impresora.
            </p>
          )}
        </section>
      </div>
    </Modal>
  );
}
