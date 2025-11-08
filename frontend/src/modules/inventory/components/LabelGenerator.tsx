import React from "react";

import { downloadDeviceLabelPdf } from "../../../api";
import { useAuth } from "../../../auth/useAuth";

type Props = {
  open?: boolean;
  onClose?: () => void;
  storeId: number | null;
  storeName?: string | null;
  deviceId?: string | null;
  deviceName?: string | null;
  sku?: string | null;
};

const DEFAULT_REASON = "Impresión de etiqueta";

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
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [filename, setFilename] = React.useState<string>("");
  const [success, setSuccess] = React.useState(false);
  const [previewUrlState, setPreviewUrlState] = React.useState<string | null>(null);
  const previewRef = React.useRef<string | null>(null);

  const updatePreviewUrl = React.useCallback((next: string | null) => {
    const current = previewRef.current;
    if (current && current !== next) {
      URL.revokeObjectURL(current);
    }
    previewRef.current = next;
    setPreviewUrlState(next);
  }, []);

  const resetState = React.useCallback(() => {
    setReason(DEFAULT_REASON);
    setError(null);
    setFilename("");
    setSuccess(false);
    setLoading(false);
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

  const parsedDeviceId = React.useMemo(() => {
    if (!deviceId) {
      return null;
    }
    const numeric = Number(deviceId);
    return Number.isFinite(numeric) ? numeric : null;
  }, [deviceId]);

  const canGenerate = Boolean(storeId) && parsedDeviceId !== null && Boolean(accessToken);

  const handleGenerate = React.useCallback(async () => {
    if (!canGenerate) {
      setError("Selecciona un producto y una sucursal para generar la etiqueta.");
      return;
    }
    const trimmedReason = reason.trim();
    if (trimmedReason.length < 5) {
      setError("Escribe un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      setSuccess(false);
      const token = accessToken;
      if (!token) {
        throw new Error("Tu sesión no está disponible. Inicia sesión nuevamente.");
      }
      const { blob, filename: suggested } = await downloadDeviceLabelPdf(
        token,
        storeId as number,
        parsedDeviceId as number,
        trimmedReason,
      );
      const objectUrl = URL.createObjectURL(blob);
      updatePreviewUrl(objectUrl);
      setFilename(suggested);
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
  }, [accessToken, canGenerate, parsedDeviceId, reason, storeId, updatePreviewUrl]);

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
          {previewUrl ? (
            <div style={{ display: "grid", gap: 12 }}>
              <iframe
                title="Vista previa de etiqueta"
                src={previewUrl}
                style={{ width: "100%", height: 360, border: "1px solid rgba(56, 189, 248, 0.3)", borderRadius: 8 }}
              />
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <a
                  href={previewUrl}
                  download={filename || "etiqueta.pdf"}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: "#38bdf8",
                    color: "#0f172a",
                    fontWeight: 600,
                    textDecoration: "none",
                  }}
                >
                  Descargar PDF
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
          )}
        </section>

        <footer style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
          <button onClick={handleClose} style={{ padding: "8px 12px", borderRadius: 8 }}>
            Cancelar
          </button>
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
