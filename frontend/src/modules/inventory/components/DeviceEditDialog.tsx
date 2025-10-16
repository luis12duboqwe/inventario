import { FormEvent, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import type { Device, DeviceUpdateInput } from "../../../api";

type Props = {
  device: Device | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (updates: DeviceUpdateInput, reason: string) => Promise<void>;
};

type FormState = {
  name: string;
  modelo: string;
  marca: string;
  color: string;
  estado: Device["estado_comercial"] | "";
  quantity: string;
  unitPrice: string;
  costoUnitario: string;
  margen: string;
  garantia: string;
  lote: string;
  fechaCompra: string;
  capacidad: string;
  proveedor: string;
  imei: string;
  serial: string;
};

const estadoOptions: Array<{ value: Device["estado_comercial"] | ""; label: string }> = [
  { value: "", label: "Sin estado" },
  { value: "nuevo", label: "Nuevo" },
  { value: "A", label: "Grado A" },
  { value: "B", label: "Grado B" },
  { value: "C", label: "Grado C" },
];

function DeviceEditDialog({ device, open, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<FormState>(() => ({
    name: "",
    modelo: "",
    marca: "",
    color: "",
    estado: "",
    quantity: "",
    unitPrice: "",
    costoUnitario: "",
    margen: "",
    garantia: "",
    lote: "",
    fechaCompra: "",
    capacidad: "",
    proveedor: "",
    imei: "",
    serial: "",
  }));
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!device || !open) {
      return;
    }
    setForm({
      name: device.name,
      modelo: device.modelo ?? "",
      marca: device.marca ?? "",
      color: device.color ?? "",
      estado: device.estado_comercial ?? "",
      quantity: "",
      unitPrice: device.unit_price ? String(device.unit_price) : "",
      costoUnitario: device.costo_unitario ? String(device.costo_unitario) : "",
      margen: device.margen_porcentaje ? String(device.margen_porcentaje) : "",
      garantia: device.garantia_meses ? String(device.garantia_meses) : "",
      lote: device.lote ?? "",
      fechaCompra: device.fecha_compra ?? "",
      capacidad: device.capacidad_gb ? String(device.capacidad_gb) : "",
      proveedor: device.proveedor ?? "",
      imei: device.imei ?? "",
      serial: device.serial ?? "",
    });
    setReason("");
    setError(null);
  }, [device, open]);

  const dialogTitle = useMemo(() => {
    if (!device) {
      return "Editar dispositivo";
    }
    return `Editar ${device.sku}`;
  }, [device]);

  const handleChange = <K extends keyof FormState>(field: K, value: FormState[K]) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const closeDialog = () => {
    if (isSubmitting) {
      return;
    }
    onClose();
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!device) {
      return;
    }
    if (!form.name.trim()) {
      setError("El nombre comercial es obligatorio.");
      return;
    }
    const normalizedReason = reason.trim();
    if (normalizedReason.length < 5) {
      setError("Ingresa un motivo corporativo de al menos 5 caracteres.");
      return;
    }

    const toNullableString = (value: string) => {
      const normalized = value.trim();
      return normalized.length > 0 ? normalized : null;
    };

    const toNullableNumber = (value: string) => {
      const normalized = value.trim();
      if (!normalized) {
        return null;
      }
      const parsed = Number(normalized.replace(/,/g, ""));
      if (!Number.isFinite(parsed)) {
        return null;
      }
      return parsed;
    };

    const updates: DeviceUpdateInput = {};

    const normalizedQuantity = form.quantity.trim();
    if (normalizedQuantity.length > 0) {
      const parsedQuantity = Number(normalizedQuantity);
      if (!Number.isInteger(parsedQuantity) || parsedQuantity < 0) {
        setError("Ingresa un número entero mayor o igual a cero para las existencias.");
        return;
      }
      if (parsedQuantity !== device.quantity) {
        updates.quantity = parsedQuantity;
      }
    }

    if (form.name.trim() !== device.name) {
      updates.name = form.name.trim();
    }

    const normalizedModelo = toNullableString(form.modelo);
    if (normalizedModelo !== (device.modelo ?? null)) {
      updates.modelo = normalizedModelo;
    }

    const normalizedMarca = toNullableString(form.marca);
    if (normalizedMarca !== (device.marca ?? null)) {
      updates.marca = normalizedMarca;
    }

    const normalizedColor = toNullableString(form.color);
    if (normalizedColor !== (device.color ?? null)) {
      updates.color = normalizedColor;
    }

    const normalizedProveedor = toNullableString(form.proveedor);
    if (normalizedProveedor !== (device.proveedor ?? null)) {
      updates.proveedor = normalizedProveedor;
    }

    const normalizedImei = toNullableString(form.imei);
    if (normalizedImei !== (device.imei ?? null)) {
      updates.imei = normalizedImei;
    }

    const normalizedSerial = toNullableString(form.serial);
    if (normalizedSerial !== (device.serial ?? null)) {
      updates.serial = normalizedSerial;
    }

    const normalizedLote = toNullableString(form.lote);
    if (normalizedLote !== (device.lote ?? null)) {
      updates.lote = normalizedLote;
    }

    const normalizedEstado = form.estado ? form.estado : null;
    if (normalizedEstado !== (device.estado_comercial ?? null)) {
      updates.estado_comercial = normalizedEstado;
    }

    const normalizedCapacidad = toNullableNumber(form.capacidad);
    if (normalizedCapacidad !== (device.capacidad_gb ?? null)) {
      updates.capacidad_gb = normalizedCapacidad;
    }

    const normalizedGarantia = toNullableNumber(form.garantia);
    if (normalizedGarantia !== (device.garantia_meses ?? null)) {
      updates.garantia_meses = normalizedGarantia;
    }

    const normalizedUnitPrice = toNullableNumber(form.unitPrice);
    if (normalizedUnitPrice !== (device.unit_price ?? null)) {
      updates.unit_price = normalizedUnitPrice;
    }

    const normalizedCostoUnitario = toNullableNumber(form.costoUnitario);
    if (normalizedCostoUnitario !== (device.costo_unitario ?? null)) {
      updates.costo_unitario = normalizedCostoUnitario;
    }

    const normalizedMargen = toNullableNumber(form.margen);
    if (normalizedMargen !== (device.margen_porcentaje ?? null)) {
      updates.margen_porcentaje = normalizedMargen;
    }

    const normalizedFecha = toNullableString(form.fechaCompra);
    if (normalizedFecha !== (device.fecha_compra ?? null)) {
      updates.fecha_compra = normalizedFecha;
    }

    if (Object.keys(updates).length === 0) {
      setError("Realiza al menos un cambio antes de guardar.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit(updates, normalizedReason);
      onClose();
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "No fue posible actualizar el dispositivo";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {open && device ? (
        <motion.div
          className="device-edit-dialog__backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="device-edit-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={dialogTitle}
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <header className="device-edit-dialog__header">
              <div>
                <h2>{dialogTitle}</h2>
                <p className="muted-text">Actualiza la ficha del dispositivo sin perder la trazabilidad corporativa.</p>
              </div>
              <button type="button" className="btn btn--ghost" onClick={closeDialog} disabled={isSubmitting}>
                Cerrar
              </button>
            </header>
            <form onSubmit={handleSubmit} className="device-edit-dialog__form">
              <div className="device-edit-dialog__grid">
                <label>
                  <span>Nombre comercial</span>
                  <input
                    value={form.name}
                    onChange={(event) => handleChange("name", event.target.value)}
                    required
                    maxLength={120}
                  />
                </label>
                <label>
                  <span>Modelo</span>
                  <input
                    value={form.modelo}
                    onChange={(event) => handleChange("modelo", event.target.value)}
                    maxLength={120}
                  />
                </label>
                <label>
                  <span>Marca</span>
                  <input
                    value={form.marca}
                    onChange={(event) => handleChange("marca", event.target.value)}
                    maxLength={80}
                  />
                </label>
                <label>
                  <span>Color</span>
                  <input
                    value={form.color}
                    onChange={(event) => handleChange("color", event.target.value)}
                    maxLength={60}
                  />
                </label>
                <label>
                  <span>Proveedor</span>
                  <input
                    value={form.proveedor}
                    onChange={(event) => handleChange("proveedor", event.target.value)}
                    maxLength={120}
                  />
                </label>
                <label>
                  <span>Estado comercial</span>
                  <select
                    value={form.estado}
                    onChange={(event) => handleChange("estado", event.target.value as FormState["estado"])}
                  >
                    {estadoOptions.map((option) => (
                      <option key={option.value || "none"} value={option.value ?? ""}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Existencias disponibles</span>
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={form.quantity}
                    onChange={(event) => handleChange("quantity", event.target.value)}
                    placeholder={`Actual: ${device.quantity}`}
                  />
                  <small className="device-edit-dialog__hint muted-text">
                    Deja el campo vacío para conservar el total actual o ingresa el valor corregido.
                  </small>
                </label>
                <label>
                  <span>Capacidad (GB)</span>
                  <input
                    type="number"
                    min={0}
                    value={form.capacidad}
                    onChange={(event) => handleChange("capacidad", event.target.value)}
                  />
                </label>
                <label>
                  <span>Precio unitario (MXN)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={form.unitPrice}
                    onChange={(event) => handleChange("unitPrice", event.target.value)}
                  />
                </label>
                <label>
                  <span>Costo unitario (MXN)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={form.costoUnitario}
                    onChange={(event) => handleChange("costoUnitario", event.target.value)}
                  />
                </label>
                <label>
                  <span>Margen (%)</span>
                  <input
                    type="number"
                    min={0}
                    step={0.01}
                    value={form.margen}
                    onChange={(event) => handleChange("margen", event.target.value)}
                  />
                </label>
                <label>
                  <span>Garantía (meses)</span>
                  <input
                    type="number"
                    min={0}
                    value={form.garantia}
                    onChange={(event) => handleChange("garantia", event.target.value)}
                  />
                </label>
                <label>
                  <span>IMEI</span>
                  <input
                    value={form.imei}
                    onChange={(event) => handleChange("imei", event.target.value)}
                    maxLength={18}
                  />
                </label>
                <label>
                  <span>Serie</span>
                  <input
                    value={form.serial}
                    onChange={(event) => handleChange("serial", event.target.value)}
                    maxLength={120}
                  />
                </label>
                <label>
                  <span>Lote</span>
                  <input
                    value={form.lote}
                    onChange={(event) => handleChange("lote", event.target.value)}
                    maxLength={80}
                  />
                </label>
                <label>
                  <span>Fecha de compra</span>
                  <input
                    type="date"
                    value={form.fechaCompra}
                    onChange={(event) => handleChange("fechaCompra", event.target.value)}
                  />
                </label>
              </div>
              <label className="device-edit-dialog__reason">
                <span>Motivo corporativo</span>
                <textarea
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  minLength={5}
                  maxLength={255}
                  required
                  placeholder="Describe brevemente la razón de la actualización"
                  rows={3}
                />
              </label>
              {error ? <p className="device-edit-dialog__error">{error}</p> : null}
              <div className="device-edit-dialog__actions">
                <button type="button" className="btn btn--ghost" onClick={closeDialog} disabled={isSubmitting}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn--primary" disabled={isSubmitting}>
                  {isSubmitting ? "Guardando…" : "Guardar cambios"}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

export default DeviceEditDialog;
