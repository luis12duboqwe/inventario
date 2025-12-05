import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";

import type { Device, DeviceUpdateInput } from "@api/inventory";
import Modal from "@components/ui/Modal";
import Button from "@components/ui/Button";
import "./DeviceEditDialog.css";

type Props = {
  device: Device | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (updates: DeviceUpdateInput, reason: string) => Promise<void>;
};

type FormValues = {
  name: string;
  modelo: string;
  marca: string;
  color: string;
  estado: Device["estado_comercial"] | "";
  estadoInventario: string;
  quantity: string;
  unitPrice: string;
  costoUnitario: string;
  margen: string;
  garantia: string;
  lote: string;
  fechaCompra: string;
  fechaIngreso: string;
  capacidadGb: string;
  capacidadTexto: string;
  categoria: string;
  condicion: string;
  proveedor: string;
  ubicacion: string;
  imei: string;
  serial: string;
  descripcion: string;
  imagenUrl: string;
  imeisAdicionales: string;
  imagenes: string;
  enlaces: string;
  reason: string;
};

const estadoOptions: Array<{ value: Device["estado_comercial"] | ""; label: string }> = [
  { value: "", label: "Sin estado" },
  { value: "nuevo", label: "Nuevo" },
  { value: "A", label: "Grado A" },
  { value: "B", label: "Grado B" },
  { value: "C", label: "Grado C" },
];

function DeviceEditDialog({ device, open, onClose, onSubmit }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting, errors },
    setError: setFormError,
  } = useForm<FormValues>();

  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!device || !open) {
      return;
    }
    const toTextareaList = (items?: string[] | null) =>
      items && items.length > 0 ? items.join("\n") : "";
    const toLinkTextareaList = (links?: Array<{ titulo?: string | null; url: string }> | null) =>
      links && links.length > 0
        ? links.map((link) => `${(link.titulo ?? "Recurso").trim()}|${link.url.trim()}`).join("\n")
        : "";

    reset({
      name: device.name,
      modelo: device.modelo ?? "",
      marca: device.marca ?? "",
      color: device.color ?? "",
      estado: device.estado_comercial ?? "",
      estadoInventario: device.estado ?? "",
      quantity: "",
      unitPrice:
        device.precio_venta != null
          ? String(device.precio_venta)
          : device.unit_price != null
          ? String(device.unit_price)
          : "",
      costoUnitario:
        device.costo_compra != null
          ? String(device.costo_compra)
          : device.costo_unitario != null
          ? String(device.costo_unitario)
          : "",
      margen: device.margen_porcentaje ? String(device.margen_porcentaje) : "",
      garantia: device.garantia_meses ? String(device.garantia_meses) : "",
      lote: device.lote ?? "",
      fechaCompra: device.fecha_compra ?? "",
      fechaIngreso: device.fecha_ingreso ?? "",
      capacidadGb: device.capacidad_gb ? String(device.capacidad_gb) : "",
      capacidadTexto: device.capacidad ?? "",
      categoria: device.categoria ?? "",
      condicion: device.condicion ?? "",
      proveedor: device.proveedor ?? "",
      ubicacion: device.ubicacion ?? "",
      imei: device.imei ?? "",
      serial: device.serial ?? "",
      descripcion: device.descripcion ?? "",
      imagenUrl: device.imagen_url ?? "",
      imeisAdicionales: toTextareaList(device.imeis_adicionales),
      imagenes: toTextareaList(device.imagenes),
      enlaces: toLinkTextareaList(device.enlaces),
      reason: "",
    });
    // Error state is reset on close or submit start
  }, [device, open, reset]);

  const dialogTitle = useMemo(() => {
    if (!device) {
      return "Editar dispositivo";
    }
    return `Editar ${device.sku}`;
  }, [device]);

  const closeDialog = () => {
    if (isSubmitting) {
      return;
    }
    setSubmitError(null);
    onClose();
  };

  const onSubmitForm = async (data: FormValues) => {
    if (!device) return;

    const normalizedReason = data.reason.trim();

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

    const parseListField = (value: string) =>
      value
        .split(/\r?\n/)
        .map((entry) => entry.trim())
        .filter(Boolean);

    const normalizeUrl = (value: string) => {
      const trimmed = value.trim();
      if (!trimmed) {
        return null;
      }
      try {
        return new URL(trimmed).toString();
      } catch {
        try {
          return new URL(`https://${trimmed}`).toString();
        } catch {
          return null;
        }
      }
    };

    const listHasChanged = (incoming: string[], current?: string[] | null) => {
      const currentList = current ?? [];
      if (incoming.length === 0 && currentList.length === 0) {
        return false;
      }
      return incoming.join("||") !== currentList.map((item) => item.trim()).join("||");
    };

    const updates: DeviceUpdateInput = {};

    const normalizedQuantity = data.quantity.trim();
    if (normalizedQuantity.length > 0) {
      const parsedQuantity = Number(normalizedQuantity);
      if (!Number.isInteger(parsedQuantity) || parsedQuantity < 0) {
        setFormError("quantity", { message: "Ingresa un número entero mayor o igual a cero." });
        return;
      }
      if (parsedQuantity !== device.quantity) {
        updates.quantity = parsedQuantity;
      }
    }

    if (data.name.trim() !== device.name) {
      updates.name = data.name.trim();
    }

    const normalizedModelo = toNullableString(data.modelo);
    if (normalizedModelo !== (device.modelo ?? null)) {
      updates.modelo = normalizedModelo;
    }

    const normalizedCategoria = toNullableString(data.categoria);
    if (normalizedCategoria !== (device.categoria ?? null)) {
      updates.categoria = normalizedCategoria;
    }

    const normalizedCondicion = toNullableString(data.condicion);
    if (normalizedCondicion !== (device.condicion ?? null)) {
      updates.condicion = normalizedCondicion;
    }

    const normalizedMarca = toNullableString(data.marca);
    if (normalizedMarca !== (device.marca ?? null)) {
      updates.marca = normalizedMarca;
    }

    const normalizedColor = toNullableString(data.color);
    if (normalizedColor !== (device.color ?? null)) {
      updates.color = normalizedColor;
    }

    const normalizedEstadoInventario = toNullableString(data.estadoInventario);
    if (normalizedEstadoInventario !== (device.estado ?? null)) {
      updates.estado = normalizedEstadoInventario;
    }

    const normalizedProveedor = toNullableString(data.proveedor);
    if (normalizedProveedor !== (device.proveedor ?? null)) {
      updates.proveedor = normalizedProveedor;
    }

    const normalizedImei = toNullableString(data.imei);
    if (normalizedImei !== (device.imei ?? null)) {
      updates.imei = normalizedImei;
    }

    const normalizedSerial = toNullableString(data.serial);
    if (normalizedSerial !== (device.serial ?? null)) {
      updates.serial = normalizedSerial;
    }

    const normalizedLote = toNullableString(data.lote);
    if (normalizedLote !== (device.lote ?? null)) {
      updates.lote = normalizedLote;
    }

    const normalizedEstado = data.estado ? data.estado : null;
    if (normalizedEstado !== (device.estado_comercial ?? null)) {
      updates.estado_comercial = normalizedEstado;
    }

    const normalizedCapacidadGb = toNullableNumber(data.capacidadGb);
    if (normalizedCapacidadGb !== (device.capacidad_gb ?? null)) {
      updates.capacidad_gb = normalizedCapacidadGb;
    }

    const normalizedCapacidadTexto = toNullableString(data.capacidadTexto);
    if (normalizedCapacidadTexto !== (device.capacidad ?? null)) {
      updates.capacidad = normalizedCapacidadTexto;
    }

    const normalizedGarantia = toNullableNumber(data.garantia);
    if (normalizedGarantia !== (device.garantia_meses ?? null)) {
      updates.garantia_meses = normalizedGarantia;
    }

    const normalizedUnitPrice = toNullableNumber(data.unitPrice);
    if (normalizedUnitPrice !== (device.precio_venta ?? device.unit_price ?? null)) {
      updates.precio_venta = normalizedUnitPrice;
      updates.unit_price = normalizedUnitPrice;
    }

    const normalizedCostoUnitario = toNullableNumber(data.costoUnitario);
    if (normalizedCostoUnitario !== (device.costo_compra ?? device.costo_unitario ?? null)) {
      updates.costo_compra = normalizedCostoUnitario;
      updates.costo_unitario = normalizedCostoUnitario;
    }

    const normalizedMargen = toNullableNumber(data.margen);
    if (normalizedMargen !== (device.margen_porcentaje ?? null)) {
      updates.margen_porcentaje = normalizedMargen;
    }

    const normalizedFecha = toNullableString(data.fechaCompra);
    if (normalizedFecha !== (device.fecha_compra ?? null)) {
      updates.fecha_compra = normalizedFecha;
    }

    const normalizedFechaIngreso = toNullableString(data.fechaIngreso);
    if (normalizedFechaIngreso !== (device.fecha_ingreso ?? null)) {
      updates.fecha_ingreso = normalizedFechaIngreso;
    }

    const normalizedUbicacion = toNullableString(data.ubicacion);
    if (normalizedUbicacion !== (device.ubicacion ?? null)) {
      updates.ubicacion = normalizedUbicacion;
    }

    const normalizedDescripcion = toNullableString(data.descripcion);
    if (normalizedDescripcion !== (device.descripcion ?? null)) {
      updates.descripcion = normalizedDescripcion;
    }

    const normalizedImagen = toNullableString(data.imagenUrl);
    if (normalizedImagen !== (device.imagen_url ?? null)) {
      updates.imagen_url = normalizedImagen;
    }

    const normalizedImeisAdicionales = parseListField(data.imeisAdicionales);
    if (listHasChanged(normalizedImeisAdicionales, device.imeis_adicionales)) {
      updates.imeis_adicionales = normalizedImeisAdicionales;
    }

    const normalizedImagenes = parseListField(data.imagenes)
      .map(normalizeUrl)
      .filter((url): url is string => Boolean(url));
    if (listHasChanged(normalizedImagenes, device.imagenes)) {
      updates.imagenes = normalizedImagenes;
    }

    const normalizedEnlaces = parseListField(data.enlaces)
      .map((entry) => {
        const [rawTitle = "", rawUrl = ""] = entry.includes("|")
          ? entry.split("|", 2)
          : ["", entry];
        const normalizedLinkUrl = normalizeUrl(rawUrl ?? "");
        if (!normalizedLinkUrl) {
          return null;
        }
        const normalizedTitle = rawTitle.trim() || "Recurso";
        return { titulo: normalizedTitle, url: normalizedLinkUrl };
      })
      .filter((link): link is { titulo: string; url: string } => Boolean(link));

    const currentLinks = (device.enlaces ?? []).map(
      (link) => `${(link.titulo ?? "Recurso").trim()}|${link.url.trim()}`,
    );
    const normalizedLinkKeys = normalizedEnlaces.map(
      (link) => `${link.titulo.trim()}|${link.url.trim()}`,
    );

    const enlacesChanged =
      (normalizedEnlaces.length > 0 || currentLinks.length > 0) &&
      normalizedLinkKeys.join("||") !== currentLinks.join("||");

    if (enlacesChanged) {
      updates.enlaces = normalizedEnlaces;
    }

    if (Object.keys(updates).length === 0) {
      setSubmitError("Realiza al menos un cambio antes de guardar.");
      return;
    }

    try {
      setSubmitError(null);
      await onSubmit(updates, normalizedReason);
      onClose();
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "No fue posible actualizar el dispositivo";
      setSubmitError(message);
    }
  };

  const isOpen = open && Boolean(device);

  return (
    <Modal
      open={isOpen}
      title={dialogTitle}
      description="Actualiza la ficha del dispositivo sin perder la trazabilidad corporativa."
      onClose={closeDialog}
      size="xl"
      dismissDisabled={isSubmitting}
      footer={
        <div className="device-edit-dialog__actions">
          <Button type="button" variant="ghost" onClick={closeDialog} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" form="device-edit-form" disabled={isSubmitting}>
            {isSubmitting ? "Guardando…" : "Guardar cambios"}
          </Button>
        </div>
      }
    >
      {device ? (
        <form
          id="device-edit-form"
          onSubmit={handleSubmit(onSubmitForm)}
          className="device-edit-dialog__form"
        >
          <div className="device-edit-dialog__grid">
            <label>
              <span>Nombre comercial</span>
              <input
                {...register("name", { required: "El nombre comercial es obligatorio." })}
                maxLength={120}
              />
              {errors.name && (
                <span className="device-edit-dialog__error">{errors.name.message}</span>
              )}
            </label>
            <label>
              <span>Modelo</span>
              <input {...register("modelo")} maxLength={120} />
            </label>
            <label>
              <span>Categoría</span>
              <input {...register("categoria")} maxLength={80} />
            </label>
            <label>
              <span>Marca</span>
              <input {...register("marca")} maxLength={80} />
            </label>
            <label>
              <span>Color</span>
              <input {...register("color")} maxLength={60} />
            </label>
            <label>
              <span>Condición</span>
              <input {...register("condicion")} maxLength={60} />
            </label>
            <label>
              <span>Proveedor</span>
              <input {...register("proveedor")} maxLength={120} />
            </label>
            <label>
              <span>Estado comercial</span>
              <select {...register("estado")}>
                {estadoOptions.map((option) => (
                  <option key={option.value || "none"} value={option.value ?? ""}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Estado inventario</span>
              <input {...register("estadoInventario")} maxLength={40} />
            </label>
            <label>
              <span>Existencias disponibles</span>
              <input
                type="number"
                min={0}
                step={1}
                {...register("quantity")}
                placeholder={`Actual: ${device.quantity}`}
              />
              <small className="device-edit-dialog__hint muted-text">
                Deja el campo vacío para conservar el total actual o ingresa el valor corregido.
              </small>
              {errors.quantity && (
                <span className="device-edit-dialog__error">{errors.quantity.message}</span>
              )}
            </label>
            <label>
              <span>Capacidad (GB)</span>
              <input type="number" min={0} {...register("capacidadGb")} />
            </label>
            <label>
              <span>Capacidad (texto)</span>
              <input {...register("capacidadTexto")} maxLength={80} />
            </label>
            <label>
              <span>Precio de venta (MXN)</span>
              <input type="number" min={0} step={0.01} {...register("unitPrice")} />
            </label>
            <label>
              <span>Costo unitario (MXN)</span>
              <input type="number" min={0} step={0.01} {...register("costoUnitario")} />
            </label>
            <label>
              <span>Margen (%)</span>
              <input type="number" min={0} step={0.01} {...register("margen")} />
            </label>
            <label>
              <span>Garantía (meses)</span>
              <input type="number" min={0} {...register("garantia")} />
            </label>
            <label>
              <span>IMEI</span>
              <input {...register("imei")} maxLength={18} />
            </label>
            <label>
              <span>IMEIs adicionales</span>
              <textarea
                {...register("imeisAdicionales")}
                placeholder="Ingresa un IMEI por línea"
                rows={3}
              />
              <small className="device-edit-dialog__hint muted-text">
                Limpia espacios extra y usa una línea por IMEI para evitar duplicados o registros
                sucios.
              </small>
            </label>
            <label>
              <span>Serie</span>
              <input {...register("serial")} maxLength={120} />
            </label>
            <label>
              <span>Lote</span>
              <input {...register("lote")} maxLength={80} />
            </label>
            <label>
              <span>Ubicación</span>
              <input {...register("ubicacion")} maxLength={120} />
            </label>
            <label>
              <span>Fecha de compra</span>
              <input type="date" {...register("fechaCompra")} />
            </label>
            <label>
              <span>Fecha de ingreso</span>
              <input type="date" {...register("fechaIngreso")} />
            </label>
            <label>
              <span>Descripción</span>
              <textarea {...register("descripcion")} maxLength={1024} rows={2} />
            </label>
            <label>
              <span>URL de imagen</span>
              <input type="url" {...register("imagenUrl")} maxLength={255} />
            </label>
            <label>
              <span>Imágenes adicionales</span>
              <textarea
                {...register("imagenes")}
                placeholder="https://cdn.softmobile.test/foto.png"
                rows={3}
              />
              <small className="device-edit-dialog__hint muted-text">
                Escribe una URL por línea; agregamos https:// automáticamente si falta y omitimos
                enlaces vacíos.
              </small>
            </label>
            <label>
              <span>Enlaces relacionados</span>
              <textarea
                {...register("enlaces")}
                placeholder="Manual|https://softmobile.test/manual.pdf"
                rows={3}
              />
              <small className="device-edit-dialog__hint muted-text">
                Usa «Título|URL» por línea o solo la URL; el título se normaliza y los espacios se
                eliminan.
              </small>
            </label>
          </div>
          <label className="device-edit-dialog__reason">
            <span>Motivo corporativo</span>
            <textarea
              {...register("reason", {
                required: "El motivo es obligatorio.",
                minLength: { value: 5, message: "Ingresa al menos 5 caracteres." },
              })}
              maxLength={255}
              placeholder="Describe brevemente la razón de la actualización"
              rows={3}
            />
            {errors.reason && (
              <span className="device-edit-dialog__error">{errors.reason.message}</span>
            )}
          </label>
          {submitError ? <p className="device-edit-dialog__error">{submitError}</p> : null}
        </form>
      ) : null}
    </Modal>
  );
}

export default DeviceEditDialog;
