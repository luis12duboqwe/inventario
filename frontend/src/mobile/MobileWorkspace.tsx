import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, BatteryCharging, Camera, ClipboardCheck } from "lucide-react";

import {
  registerInventoryCycleCount,
  registerInventoryReceiving,
  searchCatalogDevices,
  type CatalogDevice,
  type InventoryCountLineInput,
  type InventoryCycleCountRequest,
  type InventoryReceivingLineInput,
  type InventoryReceivingRequest,
} from "@api/inventory";
import { createSale, type SaleCreateInput } from "../../api/sales";
import { type PaymentMethod } from "../../api/types";
import PageHeader from "@components/ui/PageHeader";
import POSQuickScan from "../modules/sales/components/pos/POSQuickScan";
import { useDashboard } from "../modules/dashboard/context/DashboardContext";

type ScanLine = { id: string; identifier: string; quantity: number };
type CartLine = { id: string; device: CatalogDevice; quantity: number };

const CAMERA_SCAN_INTERVAL = 600;

type BarcodeDetectorCtor = new (config?: { formats?: string[] }) => {
  detect: (source: HTMLVideoElement) => Promise<Array<{ rawValue?: string | null }>>;
};

const getBarcodeDetector = (): BarcodeDetectorCtor | null => {
  if (typeof window === "undefined") return null;
  const maybe = (window as typeof window & { BarcodeDetector?: BarcodeDetectorCtor })
    .BarcodeDetector;
  return typeof maybe === "function" ? maybe : null;
};

type MobileWorkspaceProps = {
  title?: string;
};

function MobileWorkspace({ title = "Softmobile móvil" }: MobileWorkspaceProps) {
  const {
    token,
    stores,
    selectedStoreId,
    setSelectedStoreId,
    pushToast,
    refreshInventoryAfterTransfer,
  } = useDashboard();

  const [note, setNote] = useState("Conteo y recepción móvil");
  const [responsible, setResponsible] = useState("");
  const [reference, setReference] = useState("");
  const [countLines, setCountLines] = useState<ScanLine[]>([]);
  const [receivingLines, setReceivingLines] = useState<ScanLine[]>([]);
  const [loading, setLoading] = useState(false);

  // POS State
  const [mode, setMode] = useState<"inventory" | "pos">("inventory");
  const [cartLines, setCartLines] = useState<CartLine[]>([]);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("CASH");

  const [lookupQuery, setLookupQuery] = useState("");
  const [lookupResults, setLookupResults] = useState<CatalogDevice[]>([]);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanCooldownRef = useRef<number>(0);

  const selectedStore = useMemo(
    () => stores.find((store) => store.id === selectedStoreId) ?? null,
    [selectedStoreId, stores],
  );

  useEffect(() => {
    if (!token) return;
    if (!lookupQuery.trim()) {
      setLookupResults([]);
      return;
    }
    setLookupLoading(true);
    setLookupError(null);
    const timer = window.setTimeout(() => {
      searchCatalogDevices(token, {
        imei: lookupQuery.trim(),
        serial: lookupQuery.trim(),
      })
        .then(setLookupResults)
        .catch((error: unknown) => {
          const message =
            error instanceof Error
              ? error.message
              : "No fue posible consultar el inventario en modo móvil.";
          setLookupError(message);
        })
        .finally(() => setLookupLoading(false));
    }, 240);

    return () => {
      window.clearTimeout(timer);
    };
  }, [lookupQuery, token]);

  const stopTracks = useCallback((stream: MediaStream | null) => {
    stream?.getTracks().forEach((track) => track.stop());
  }, []);

  const stopCamera = useCallback(() => {
    stopTracks(streamRef.current);
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, [stopTracks]);

  const addCountLine = useCallback((identifier: string) => {
    setCountLines((current) => {
      const existing = current.find((line) => line.identifier === identifier);
      if (existing) {
        return current.map((line) =>
          line.identifier === identifier ? { ...line, quantity: line.quantity + 1 } : line,
        );
      }
      return [{ id: crypto.randomUUID(), identifier, quantity: 1 }, ...current].slice(0, 25);
    });
  }, []);

  const addReceivingLine = useCallback((identifier: string) => {
    setReceivingLines((current) => {
      const existing = current.find((line) => line.identifier === identifier);
      if (existing) {
        return current.map((line) =>
          line.identifier === identifier ? { ...line, quantity: line.quantity + 1 } : line,
        );
      }
      return [{ id: crypto.randomUUID(), identifier, quantity: 1 }, ...current].slice(0, 25);
    });
  }, []);

  const handleCameraDetection = useCallback(
    async (value: string) => {
      if (mode === "pos") {
        try {
          let results = await searchCatalogDevices(token, { imei: value });
          if (results.length === 0) {
            results = await searchCatalogDevices(token, { serial: value });
          }
          if (results.length > 0) {
            addToCart(results[0]);
            pushToast({ message: `Agregado: ${results[0].name}`, variant: "success" });
          } else {
            pushToast({ message: `No encontrado: ${value}`, variant: "error" });
          }
        } catch (e) {
          pushToast({ message: "Error al buscar producto", variant: "error" });
        }
      } else {
        addCountLine(value);
        addReceivingLine(value);
        pushToast({ message: `Capturado ${value} desde la cámara.`, variant: "success" });
      }
    },
    [addCountLine, addReceivingLine, pushToast, mode, addToCart, token],
  );

  useEffect(() => {
    if (!cameraEnabled) {
      stopCamera();
      return;
    }
    let cancelled = false;
    setCameraError(null);
    const supportsMedia = typeof navigator !== "undefined" && !!navigator.mediaDevices;
    const detectorCtor = getBarcodeDetector();
    const supportsDetector = Boolean(detectorCtor);
    if (!supportsMedia) {
      setCameraError("El dispositivo no permite abrir la cámara desde el navegador.");
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((stream) => {
        if (cancelled) {
          stopTracks(stream);
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          void videoRef.current.play().catch(() => {
            setCameraError("No fue posible reproducir la vista previa de la cámara.");
          });
        }
        if (!supportsDetector) {
          setCameraError("BarcodeDetector no disponible; usa el lector Bluetooth.");
          return;
        }
        const detector = detectorCtor
          ? new detectorCtor({ formats: ["qr_code", "code_128", "ean_13", "ean_8"] })
          : null;
        const scan = async () => {
          if (!cameraEnabled || !videoRef.current || !detector) return;
          if (Date.now() - scanCooldownRef.current < CAMERA_SCAN_INTERVAL) {
            window.requestAnimationFrame(scan);
            return;
          }
          try {
            const detections = await detector.detect(videoRef.current);
            const first = detections.at(0);
            const value = first?.rawValue?.trim();
            if (value) {
              scanCooldownRef.current = Date.now();
              await handleCameraDetection(value);
            }
          } catch (error) {
            const message =
              error instanceof Error
                ? error.message
                : "No fue posible leer el código desde la cámara.";
            setCameraError(message);
          }
          window.requestAnimationFrame(scan);
        };
        window.requestAnimationFrame(scan);
      })
      .catch(() => {
        setCameraError("No se pudo activar la cámara. Revisa permisos y vuelve a intentar.");
      });
    return () => {
      cancelled = true;
      stopCamera();
    };
  }, [cameraEnabled, handleCameraDetection, stopCamera, stopTracks]);

  const addToCart = useCallback((device: CatalogDevice) => {
    setCartLines((current) => {
      const existing = current.find((line) => line.device.id === device.id);
      if (existing) {
        return current.map((line) =>
          line.device.id === device.id ? { ...line, quantity: line.quantity + 1 } : line,
        );
      }
      return [{ id: crypto.randomUUID(), device, quantity: 1 }, ...current];
    });
  }, []);

  const handleCheckout = async () => {
    if (!selectedStoreId) {
      pushToast({ message: "Selecciona una sucursal.", variant: "error" });
      return;
    }
    if (cartLines.length === 0) {
      pushToast({ message: "El carrito está vacío.", variant: "warning" });
      return;
    }

    try {
      setLoading(true);
      const payload: SaleCreateInput = {
        store_id: selectedStoreId,
        payment_method: paymentMethod,
        items: cartLines.map((line) => ({
          device_id: line.device.id,
          quantity: line.quantity,
        })),
        notes: "Venta móvil",
      };

      await createSale(token, payload, "Venta móvil POS");
      pushToast({ message: "Venta registrada exitosamente.", variant: "success" });
      setCartLines([]);
      await refreshInventoryAfterTransfer();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Error al procesar venta";
      pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async (raw: string) => {
    const value = raw.trim();
    if (!value) return "Lectura vacía";

    if (mode === "pos") {
      try {
        // Intentar búsqueda exacta por IMEI/Serie
        let results = await searchCatalogDevices(token, { imei: value });
        if (results.length === 0) {
          results = await searchCatalogDevices(token, { serial: value });
        }

        if (results.length > 0) {
          const device = results[0];
          addToCart(device);
          pushToast({ message: `Agregado: ${device.name}`, variant: "success" });
          return { label: device.name };
        } else {
          pushToast({ message: "Producto no encontrado", variant: "error" });
          return "No encontrado";
        }
      } catch (e) {
        console.error(e);
        return "Error búsqueda";
      }
    } else {
      addCountLine(value);
      addReceivingLine(value);
      return { label: value };
    }
  };

  const handleUpdateLine = (
    list: ScanLine[],
    id: string,
    quantity: number,
    setter: (lines: ScanLine[]) => void,
  ) => {
    setter(
      list.map((line) => (line.id === id ? { ...line, quantity: Math.max(0, quantity) } : line)),
    );
  };

  const handleRemoveLine = (list: ScanLine[], id: string, setter: (lines: ScanLine[]) => void) => {
    setter(list.filter((line) => line.id !== id));
  };

  const mapLinesToCountPayload = (lines: ScanLine[]): InventoryCountLineInput[] =>
    lines
      .filter((line) => line.quantity > 0)
      .map((line) => ({ imei: line.identifier, counted: line.quantity }));

  const mapLinesToReceivingPayload = (lines: ScanLine[]): InventoryReceivingLineInput[] =>
    lines
      .filter((line) => line.quantity > 0)
      .map((line) => ({ imei: line.identifier, quantity: line.quantity }));

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedStoreId) {
      pushToast({
        message: "Selecciona una sucursal para registrar el movimiento.",
        variant: "error",
      });
      return;
    }
    const trimmedNote = note.trim();
    if (trimmedNote.length < 5) {
      pushToast({
        message: "El motivo corporativo debe tener al menos 5 caracteres.",
        variant: "warning",
      });
      return;
    }
    const countPayload: InventoryCycleCountRequest = {
      store_id: selectedStoreId,
      note: trimmedNote,
      lines: mapLinesToCountPayload(countLines),
      ...(responsible.trim() ? { responsible: responsible.trim() } : {}),
      ...(reference.trim() ? { reference: reference.trim() } : {}),
    };
    const receivingPayload: InventoryReceivingRequest = {
      store_id: selectedStoreId,
      note: trimmedNote,
      lines: mapLinesToReceivingPayload(receivingLines),
      ...(responsible.trim() ? { responsible: responsible.trim() } : {}),
      ...(reference.trim() ? { reference: reference.trim() } : {}),
    };
    if (countPayload.lines.length === 0 && receivingPayload.lines.length === 0) {
      pushToast({ message: "Escanea o captura al menos un código.", variant: "warning" });
      return;
    }
    try {
      setLoading(true);
      const promises: Promise<unknown>[] = [];
      if (receivingPayload.lines.length > 0) {
        promises.push(registerInventoryReceiving(token, receivingPayload, trimmedNote));
      }
      if (countPayload.lines.length > 0) {
        promises.push(registerInventoryCycleCount(token, countPayload, trimmedNote));
      }
      await Promise.all(promises);
      pushToast({ message: "Movimientos móviles registrados.", variant: "success" });
      setCountLines([]);
      setReceivingLines([]);
      await refreshInventoryAfterTransfer();
    } catch (error: unknown) {
      const fallback = "No se pudo enviar el movimiento móvil.";
      pushToast({
        message: error instanceof Error ? error.message || fallback : fallback,
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const totalCount = useMemo(
    () => countLines.reduce((sum, line) => sum + line.quantity, 0),
    [countLines],
  );
  const totalReceiving = useMemo(
    () => receivingLines.reduce((sum, line) => sum + line.quantity, 0),
    [receivingLines],
  );

  return (
    <div className="mobile-workspace">
      <PageHeader
        title={title}
        description={
          mode === "pos"
            ? "Punto de venta móvil express."
            : "Conteos rápidos, recepciones y consulta express."
        }
      />

      <div className="flex gap-2 mb-4 px-4">
        <button
          className={`btn ${mode === "inventory" ? "btn--primary" : "btn--ghost"} flex-1`}
          onClick={() => setMode("inventory")}
        >
          Inventario
        </button>
        <button
          className={`btn ${mode === "pos" ? "btn--primary" : "btn--ghost"} flex-1`}
          onClick={() => setMode("pos")}
        >
          Venta POS
        </button>
      </div>

      <div className="mobile-grid">
        <section className="mobile-card">
          <header className="mobile-card__header">
            <div>
              <p className="eyebrow">Escucha activa</p>
              <h2>Escáner rápido</h2>
              <p className="muted-text">
                Usa tu lector Bluetooth o la cámara del dispositivo para poblar conteos y
                recepciones.
              </p>
            </div>
            <div className="mobile-card__actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setCameraEnabled((current) => !current)}
                aria-pressed={cameraEnabled}
              >
                <Camera size={18} aria-hidden />{" "}
                {cameraEnabled ? "Detener cámara" : "Activar cámara"}
              </button>
            </div>
          </header>

          <div className="mobile-scan-wrapper">
            <POSQuickScan
              onSubmit={handleScan}
              captureTimeout={35}
              onEnabledChange={() => setCameraEnabled(false)}
            />
            <div className="mobile-camera-preview" aria-live="polite">
              <video
                ref={videoRef}
                muted
                playsInline
                className={cameraEnabled ? "camera-live" : "camera-idle"}
              />
              {cameraError && (
                <p className="mobile-inline-alert">
                  <AlertCircle size={16} aria-hidden /> {cameraError}
                </p>
              )}
            </div>
          </div>
        </section>

        {mode === "inventory" ? (
          <section className="mobile-card">
            <header className="mobile-card__header">
              <div>
                <p className="eyebrow">Inventario en campo</p>
                <h2>Conteo y recepción</h2>
                <p className="muted-text">
                  Ajusta cantidades y envía los movimientos con motivo corporativo obligatorio.
                </p>
              </div>
              <BatteryCharging size={18} aria-hidden />
            </header>

            <form className="mobile-form" onSubmit={handleSubmit}>
              <label className="mobile-field">
                <span>Sucursal destino</span>
                <select
                  value={selectedStoreId ?? ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelectedStoreId(value ? Number(value) : null);
                  }}
                >
                  <option value="">Selecciona una sucursal</option>
                  {stores.map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="mobile-field">
                <span>Motivo corporativo</span>
                <textarea
                  required
                  minLength={5}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Ej. Conteo sorpresa en pasillo A"
                />
              </label>

              <div className="mobile-field-grid">
                <label className="mobile-field">
                  <span>Responsable</span>
                  <input
                    value={responsible}
                    onChange={(event) => setResponsible(event.target.value)}
                    placeholder="Auditor o receptor"
                  />
                </label>
                <label className="mobile-field">
                  <span>Referencia</span>
                  <input
                    value={reference}
                    onChange={(event) => setReference(event.target.value)}
                    placeholder="Folio o ticket"
                  />
                </label>
              </div>

              <div className="mobile-list">
                <div className="mobile-list__title">
                  <strong>Conteo ({totalCount})</strong>
                  <small className="muted-text">Edita cantidades antes de conciliar</small>
                </div>
                {countLines.length === 0 ? (
                  <p className="muted-text">Escanea para comenzar el conteo.</p>
                ) : (
                  <ul>
                    {countLines.map((line) => (
                      <li key={line.id} className="mobile-line">
                        <span className="mobile-line__id">{line.identifier}</span>
                        <input
                          type="number"
                          min={0}
                          value={line.quantity}
                          onChange={(event) =>
                            handleUpdateLine(
                              countLines,
                              line.id,
                              Number(event.target.value),
                              setCountLines,
                            )
                          }
                        />
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() => handleRemoveLine(countLines, line.id, setCountLines)}
                          aria-label={`Eliminar ${line.identifier} del conteo`}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="mobile-list">
                <div className="mobile-list__title">
                  <strong>Recepción ({totalReceiving})</strong>
                  <small className="muted-text">Confirma piezas recibidas</small>
                </div>
                {receivingLines.length === 0 ? (
                  <p className="muted-text">Escanea para agregar recepciones.</p>
                ) : (
                  <ul>
                    {receivingLines.map((line) => (
                      <li key={line.id} className="mobile-line">
                        <span className="mobile-line__id">{line.identifier}</span>
                        <input
                          type="number"
                          min={0}
                          value={line.quantity}
                          onChange={(event) =>
                            handleUpdateLine(
                              receivingLines,
                              line.id,
                              Number(event.target.value),
                              setReceivingLines,
                            )
                          }
                        />
                        <button
                          type="button"
                          className="btn btn--ghost"
                          onClick={() =>
                            handleRemoveLine(receivingLines, line.id, setReceivingLines)
                          }
                          aria-label={`Eliminar ${line.identifier} de la recepción`}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="mobile-actions">
                <button type="submit" className="btn btn--primary" disabled={loading}>
                  {loading ? "Enviando" : "Registrar movimientos"}
                </button>
              </div>
            </form>
          </section>
        ) : (
          <section className="mobile-card">
            <header className="mobile-card__header">
              <div>
                <p className="eyebrow">Venta en piso</p>
                <h2>Carrito de compra</h2>
                <p className="muted-text">Escanea productos para agregar al ticket.</p>
              </div>
            </header>

            <div className="mobile-list">
              {cartLines.length === 0 ? (
                <p className="muted-text">Carrito vacío. Escanea un producto.</p>
              ) : (
                <ul>
                  {cartLines.map((line) => (
                    <li key={line.id} className="mobile-line">
                      <div>
                        <span className="mobile-line__id">{line.device.name}</span>
                        <div className="text-xs text-slate-400">
                          ${line.device.unit_price?.toLocaleString() ?? "0"}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <input
                          type="number"
                          value={line.quantity}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            setCartLines((prev) =>
                              prev.map((p) => (p.id === line.id ? { ...p, quantity: val } : p)),
                            );
                          }}
                          className="w-16 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-white"
                        />
                        <button
                          className="btn btn--ghost"
                          onClick={() =>
                            setCartLines((prev) => prev.filter((p) => p.id !== line.id))
                          }
                        >
                          ×
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="p-4 border-t border-slate-700">
              <div className="flex justify-between mb-4 text-lg font-bold text-white">
                <span>Total</span>
                <span>
                  $
                  {cartLines
                    .reduce((sum, line) => sum + line.quantity * (line.device.unit_price || 0), 0)
                    .toLocaleString()}
                </span>
              </div>

              <label className="mobile-field mb-4">
                <span>Método de Pago</span>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
                >
                  <option value="CASH">Efectivo</option>
                  <option value="CARD">Tarjeta</option>
                  <option value="TRANSFER">Transferencia</option>
                </select>
              </label>

              <button
                className="btn btn--primary w-full"
                onClick={handleCheckout}
                disabled={loading || cartLines.length === 0}
              >
                {loading ? "Procesando..." : "Cobrar"}
              </button>
            </div>
          </section>
        )}

        <section className="mobile-card">
          <header className="mobile-card__header">
            <div>
              <p className="eyebrow">Consulta express</p>
              <h2>Disponibilidad y estado</h2>
              <p className="muted-text">
                Busca por IMEI o serie para confirmar ubicación y estado comercial.
              </p>
            </div>
            <ClipboardCheck size={18} aria-hidden />
          </header>

          <label className="mobile-field">
            <span>IMEI o número de serie</span>
            <input
              value={lookupQuery}
              onChange={(event) => setLookupQuery(event.target.value)}
              placeholder="Ej. 356938035643809"
              inputMode="numeric"
              autoComplete="off"
            />
          </label>

          {lookupLoading && <p className="muted-text">Consultando…</p>}
          {lookupError && (
            <p className="mobile-inline-alert">
              <AlertCircle size={16} aria-hidden /> {lookupError}
            </p>
          )}

          {lookupResults.length > 0 ? (
            <ul className="mobile-lookup-results">
              {lookupResults.map((device) => (
                <li
                  key={`${device.id}-${device.imei ?? device.serial}`}
                  className="mobile-lookup-item"
                >
                  <div>
                    <p className="lookup-title">{device.modelo ?? device.name ?? "Equipo"}</p>
                    <p className="muted-text">
                      IMEI: {device.imei ?? "—"} · Serie: {device.serial ?? "—"}
                    </p>
                    <p className="muted-text">
                      Color: {device.color ?? "—"} · Capacidad: {device.capacidad_gb ?? "—"} GB
                    </p>
                  </div>
                  <div className="lookup-pill">{device.estado_comercial ?? "Sin estado"}</div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-text">Ingresa un identificador para ver resultados.</p>
          )}

          {selectedStore && (
            <p className="mobile-hint" role="status">
              Operando en <strong>{selectedStore.name}</strong>. Los movimientos enviarán cabecera{" "}
              <code>X-Reason</code> con tu motivo corporativo.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}

export default MobileWorkspace;
