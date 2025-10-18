import { ChangeEvent, useCallback, useMemo, useState } from "react";
import QRCode from "qrcode";

import ScrollableTable from "../../../components/ScrollableTable";
import { Device } from "../../../api";
import { colors } from "../../../theme/designTokens";

type Props = {
  devices: Device[];
  highlightedDeviceIds?: Set<number>;
  emptyMessage?: string;
  onEditDevice?: (device: Device) => void;
};

const estadoLabels: Record<Device["estado_comercial"] | undefined, string> = {
  nuevo: "Nuevo",
  A: "Grado A",
  B: "Grado B",
  C: "Grado C",
  undefined: "No definido",
};

const estadoTone = (estado: Device["estado_comercial"] | undefined): "success" | "info" | "warning" | "danger" => {
  switch (estado) {
    case "A":
      return "info";
    case "B":
      return "warning";
    case "C":
      return "danger";
    default:
      return "success";
  }
};

function InventoryTable({ devices, highlightedDeviceIds, emptyMessage, onEditDevice }: Props) {
  const [pageSize, setPageSize] = useState(50);
  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

  const pageSizeOptions = useMemo(() => [25, 50, 100, 250], []);

  const escapeHtml = useCallback((value: string) => {
    return value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }, []);

  const handlePageSizeChange = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    setPageSize(Number(event.target.value));
  }, []);

  const handlePrintLabel = useCallback(async (device: Device) => {
    const qrPayload = JSON.stringify({
      sku: device.sku,
      imei: device.imei ?? null,
      serial: device.serial ?? null,
    });

    let dataUrl: string;
    try {
      dataUrl = await QRCode.toDataURL(qrPayload, { width: 160, margin: 1, errorCorrectionLevel: "M" });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("No fue posible generar el código QR", error);
      window.alert("No fue posible generar la etiqueta. Intenta nuevamente.");
      return;
    }

    const printWindow = window.open("", "softmobile-print-label", "width=420,height=600");
    if (!printWindow) {
      window.alert("Debes permitir ventanas emergentes para imprimir la etiqueta.");
      return;
    }

    const modelLabel = escapeHtml(device.modelo ?? device.name);
    const skuLabel = escapeHtml(device.sku);
    const imeiLabel = device.imei ? escapeHtml(device.imei) : "—";
    const serialLabel = device.serial ? escapeHtml(device.serial) : "—";

    const html = `<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charSet="utf-8" />
    <title>Etiqueta ${modelLabel}</title>
    <style>
      * { box-sizing: border-box; }
      body { font-family: 'Segoe UI', sans-serif; background: ${colors.backgroundSecondary}; color: ${colors.textSecondary}; margin: 0; padding: 16px; }
      .label { width: 260px; border: 2px solid ${colors.accent}; border-radius: 12px; padding: 16px; margin: 0 auto; text-align: center; }
      h1 { font-size: 18px; margin: 0 0 12px; color: ${colors.accent}; }
      p { margin: 4px 0; font-size: 13px; }
      .meta { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
      .qr { margin-top: 8px; }
      img { width: 140px; height: 140px; }
    </style>
  </head>
  <body>
    <div class="label">
      <h1>${modelLabel}</h1>
      <div class="meta">
        <p><strong>SKU:</strong> ${skuLabel}</p>
        <p><strong>IMEI:</strong> ${imeiLabel}</p>
        <p><strong>Serie:</strong> ${serialLabel}</p>
      </div>
      <div class="qr">
        <img src="${dataUrl}" alt="QR del dispositivo" />
      </div>
    </div>
    <script>
      window.print();
      setTimeout(() => window.close(), 300);
    </script>
  </body>
</html>`;

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
  }, [escapeHtml]);

  return (
    <ScrollableTable
      items={devices}
      itemKey={(device) => device.id}
      pageSize={pageSize}
      renderHead={() => (
        <>
          <th scope="col">SKU</th>
          <th scope="col">Nombre</th>
          <th scope="col">Categoría</th>
          <th scope="col">Modelo</th>
          <th scope="col">Condición</th>
          <th scope="col">Estado</th>
          <th scope="col">Estado inventario</th>
          <th scope="col">Ubicación</th>
          <th scope="col">Identificadores</th>
          <th scope="col">Cantidad</th>
          <th scope="col">Costo compra</th>
          <th scope="col">Precio de venta</th>
          <th scope="col">Valor total</th>
          <th scope="col" className="actions-column">Acciones</th>
        </>
      )}
      renderRow={(device) => (
        <tr className={highlightedDeviceIds?.has(device.id) ? "inventory-row low-stock" : "inventory-row"}>
          <td data-label="SKU">{device.sku}</td>
          <td data-label="Nombre">{device.name}</td>
          <td data-label="Categoría">{device.categoria ?? "—"}</td>
          <td data-label="Modelo">{device.modelo ?? "—"}</td>
          <td data-label="Condición">{device.condicion ?? "—"}</td>
          <td data-label="Estado">
            <span className={`status-chip ${estadoTone(device.estado_comercial)}`}>
              {estadoLabels[device.estado_comercial]}
            </span>
          </td>
          <td data-label="Estado inventario">{device.estado ?? "—"}</td>
          <td data-label="Ubicación">{device.ubicacion ?? "—"}</td>
          <td data-label="Identificadores">
            <div className="identifier-stack">
              {device.imei ? <span>IMEI catálogo: {device.imei}</span> : null}
              {device.serial ? <span>Serie catálogo: {device.serial}</span> : null}
              {device.identifier?.imei_1 ? <span>IMEI 1: {device.identifier.imei_1}</span> : null}
              {device.identifier?.imei_2 ? <span>IMEI 2: {device.identifier.imei_2}</span> : null}
              {device.identifier?.numero_serie ? (
                <span>Serie extendida: {device.identifier.numero_serie}</span>
              ) : null}
              {device.identifier?.estado_tecnico ? (
                <span>Estado técnico: {device.identifier.estado_tecnico}</span>
              ) : null}
              {device.identifier?.observaciones ? (
                <span>Notas: {device.identifier.observaciones}</span>
              ) : null}
              {!device.imei &&
              !device.serial &&
              !device.identifier?.imei_1 &&
              !device.identifier?.imei_2 &&
              !device.identifier?.numero_serie ? (
                <span className="muted-text">—</span>
              ) : null}
            </div>
          </td>
          <td data-label="Cantidad">{device.quantity}</td>
          <td data-label="Costo compra">
            {currencyFormatter.format(device.costo_compra ?? device.costo_unitario ?? 0)}
          </td>
          <td data-label="Precio de venta">
            {currencyFormatter.format(device.precio_venta ?? device.unit_price ?? 0)}
          </td>
          <td data-label="Valor total">{currencyFormatter.format(device.inventory_value)}</td>
          <td data-label="Acciones">
            <div className="inventory-actions">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => {
                  void handlePrintLabel(device);
                }}
              >
                Imprimir etiqueta
              </button>
              {onEditDevice ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => onEditDevice(device)}
                >
                  Editar ficha
                </button>
              ) : null}
            </div>
          </td>
        </tr>
      )}
      emptyMessage={emptyMessage ?? "No hay dispositivos registrados para esta sucursal."}
      title="Inventario corporativo"
      ariaLabel="Tabla de inventario corporativo"
      footer={(
        <div className="inventory-table__footer">
          <label className="inventory-table__page-size">
            <span>Registros por página</span>
            <select value={pageSize} onChange={handlePageSizeChange}>
              {pageSizeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <p className="inventory-table__virtualization-hint muted-text">
            Usa “Expandir vista completa” para cargar más filas mediante desplazamiento continuo.
          </p>
        </div>
      )}
    />
  );
}

export default InventoryTable;
