import { useEffect, useMemo, useState } from "react";

import { ArrowLeftRight, Send } from "lucide-react";

import Button from "@components/ui/Button";
import { getDevices, type Device } from "@api/inventory";
import { createTransferOrder } from "@api/transfers";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

const MIN_REASON_LENGTH = 5; // [PACK30-31-FRONTEND]

function InventoryTransferFormSection() {
  const {
    module: { token, stores, refreshSummary, refreshRecentMovements },
  } = useInventoryLayout();

  const [originStoreId, setOriginStoreId] = useState<number | "">("");
  const [destinationStoreId, setDestinationStoreId] = useState<number | "">("");
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [deviceId, setDeviceId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1);
  const [reference, setReference] = useState("Transferencia interna");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedDevice = useMemo(() => {
    if (typeof deviceId !== "number") {
      return null;
    }
    return devices.find((device) => device.id === deviceId) ?? null;
  }, [deviceId, devices]);

  useEffect(() => {
    if (typeof originStoreId !== "number" || !token) {
      setDevices([]);
      setDeviceId("");
      return;
    }
    let active = true;
    setIsLoadingDevices(true);
    const timeout = window.setTimeout(async () => {
      try {
        const data = await getDevices(token, originStoreId, { estado_inventario: "disponible" });
        if (active) {
          setDevices(data);
        }
      } catch (fetchError) {
        if (active) {
          const message =
            fetchError instanceof Error
              ? fetchError.message
              : "No fue posible consultar los productos disponibles.";
          setError(message);
        }
      } finally {
        if (active) {
          setIsLoadingDevices(false);
        }
      }
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [originStoreId, token]);

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();
    setFeedback(null);
    setError(null);

    if (!token) {
      setError("No hay sesión activa para registrar la transferencia.");
      return;
    }
    if (typeof originStoreId !== "number") {
      setError("Selecciona una sucursal de origen válida.");
      return;
    }
    if (typeof destinationStoreId !== "number") {
      setError("Selecciona una sucursal de destino válida.");
      return;
    }
    if (originStoreId === destinationStoreId) {
      setError("La sucursal de origen y destino deben ser diferentes.");
      return;
    }
    if (typeof deviceId !== "number") {
      setError("Selecciona un producto a transferir.");
      return;
    }
    if (!selectedDevice) {
      setError("El producto seleccionado no está disponible en la sucursal de origen.");
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0) {
      setError("La cantidad debe ser mayor a cero.");
      return;
    }
    if (selectedDevice.quantity < quantity) {
      setError("No hay stock suficiente para completar la transferencia.");
      return;
    }
    const normalizedReference = reference.trim();
    if (normalizedReference.length < MIN_REASON_LENGTH) {
      setError(`El motivo corporativo debe tener al menos ${MIN_REASON_LENGTH} caracteres.`);
      return;
    }

    setIsSubmitting(true);
    try {
      await createTransferOrder(
        token,
        {
          origin_store_id: originStoreId,
          destination_store_id: destinationStoreId,
          reason: normalizedReference,
          items: [
            {
              device_id: deviceId,
              quantity,
            },
          ],
        },
        normalizedReference,
      );
      setFeedback("Transferencia registrada correctamente.");
      setDeviceId("");
      setQuantity(1);
      setReference("Transferencia interna");
      void refreshSummary();
      void refreshRecentMovements();
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "No fue posible registrar la transferencia.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Transferir stock</h2>
          <p className="card-subtitle">
            Mueve inventario entre sucursales registrando salidas y entradas automáticas.
          </p>
        </div>
        <span className="pill neutral">
          <ArrowLeftRight size={16} aria-hidden="true" />
          <span className="sr-only">Transferencias básicas</span>
        </span>
      </header>
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          Sucursal de origen
          <select
            value={originStoreId}
            onChange={(event) =>
              setOriginStoreId(event.target.value ? Number(event.target.value) : "")
            }
            required
          >
            <option value="">Selecciona sucursal</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sucursal de destino
          <select
            value={destinationStoreId}
            onChange={(event) =>
              setDestinationStoreId(event.target.value ? Number(event.target.value) : "")
            }
            required
          >
            <option value="">Selecciona sucursal</option>
            {stores.map((store) => (
              <option key={`dest-${store.id}`} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        </label>
        <label className="span-2">
          Producto
          <select
            value={deviceId}
            onChange={(event) => setDeviceId(event.target.value ? Number(event.target.value) : "")}
            disabled={typeof originStoreId !== "number" || isLoadingDevices}
            required
          >
            <option value="">{isLoadingDevices ? "Cargando…" : "Selecciona un producto"}</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.name} · SKU {device.sku} · {device.quantity} ud
              </option>
            ))}
          </select>
        </label>
        <label>
          Cantidad
          <input
            type="number"
            min={1}
            value={quantity}
            onChange={(event) => {
              const nextValue = Number(event.target.value);
              if (Number.isNaN(nextValue)) {
                setQuantity(1);
                return;
              }
              setQuantity(Math.max(1, nextValue));
            }}
            required
          />
        </label>
        <label className="span-3">
          Motivo corporativo / Referencia
          <input
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Ej. Transferencia a sucursal Norte"
            minLength={MIN_REASON_LENGTH}
            required
          />
          <span className="muted-text">
            Se utilizará como folio y motivo en la bitácora contable. {/* [PACK30-31-FRONTEND] */}
          </span>
        </label>
        {selectedDevice ? (
          <p className="muted-text span-3">
            Stock disponible en origen: {selectedDevice.quantity} unidades. Costo unitario estimado:
            ${selectedDevice.costo_unitario?.toFixed(2) ?? "0.00"}.
          </p>
        ) : null}
        {error ? <p className="inventory-transfer-error span-3">{error}</p> : null}
        {feedback ? <p className="inventory-transfer-success span-3">{feedback}</p> : null}
        <div className="button-row span-3">
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting}
            leadingIcon={<Send size={16} />}
          >
            {isSubmitting ? "Registrando…" : "Registrar transferencia"}
          </Button>
        </div>
      </form>
    </section>
  );
}

export default InventoryTransferFormSection;
