import { ChangeEvent, useCallback, useMemo, useState, Fragment } from "react";
import { MapPin, ChevronDown, ChevronRight, Columns } from "lucide-react";
import QRCode from "qrcode";

import ScrollableTable from "../../../shared/components/ScrollableTable";
import { colors } from "../../../theme/designTokens";
import { emitClientError } from "../../../utils/clientLog";
import Modal from "@components/ui/Modal";
import {
  Device,
  getInventoryAvailability,
  type InventoryAvailabilityRecord,
} from "@api/inventory";
import { useInventoryLayout } from "../pages/context/InventoryLayoutContext";
import { formatCurrencyWithUsd } from "@/utils/locale";

type Props = {
  devices: Device[];
  highlightedDeviceIds?: Set<number>;
  emptyMessage?: string;
  onEditDevice?: (device: Device) => void;
};

const estadoLabels: Record<NonNullable<Device["estado_comercial"]>, string> = {
  nuevo: "Nuevo",
  A: "Grado A",
  B: "Grado B",
  C: "Grado C",
};

const DEFAULT_ESTADO_LABEL = "No definido";

const resolveEstadoLabel = (estado?: Device["estado_comercial"]): string => {
  if (!estado) {
    return DEFAULT_ESTADO_LABEL;
  }

  return estadoLabels[estado] ?? DEFAULT_ESTADO_LABEL;
};

const estadoTone = (
  estado: Device["estado_comercial"] | undefined,
): "success" | "info" | "warning" | "danger" => {
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

const buildAvailabilityReference = (device: Device): string => {
  const normalizedSku = device.sku?.trim().toLowerCase();
  if (normalizedSku) {
    return normalizedSku;
  }
  return `device:${device.id}`;
};

type ColumnId =
  | "expand"
  | "sku"
  | "name"
  | "category"
  | "model"
  | "condition"
  | "status"
  | "inventory_status"
  | "location"
  | "warehouse"
  | "stores"
  | "quantity"
  | "cost"
  | "price"
  | "total_value"
  | "actions";

type ColumnConfig = {
  id: ColumnId;
  label: string;
  sticky?: "left" | "right";
  alwaysVisible?: boolean;
  defaultHidden?: boolean;
};

const COLUMNS: ColumnConfig[] = [
  { id: "expand", label: "", sticky: "left", alwaysVisible: true },
  { id: "sku", label: "SKU", sticky: "left", alwaysVisible: true },
  { id: "name", label: "Nombre", sticky: "left", alwaysVisible: true },
  { id: "category", label: "Categoría" },
  { id: "model", label: "Modelo" },
  { id: "condition", label: "Condición" },
  { id: "status", label: "Estado" },
  { id: "inventory_status", label: "Estado inv.", defaultHidden: true },
  { id: "location", label: "Ubicación", defaultHidden: true },
  { id: "warehouse", label: "Almacén", defaultHidden: true },
  { id: "stores", label: "Sucursales" },
  { id: "quantity", label: "Cantidad" },
  { id: "cost", label: "Costo compra" },
  { id: "price", label: "Precio venta" },
  { id: "total_value", label: "Valor total" },
  { id: "actions", label: "Acciones", sticky: "right", alwaysVisible: true },
];

function InventoryTable({ devices, highlightedDeviceIds, emptyMessage, onEditDevice }: Props) {
  const [pageSize, setPageSize] = useState(50);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnId>>(() => {
    return new Set(COLUMNS.filter((c) => !c.defaultHidden).map((c) => c.id));
  });
  const [isColumnSelectorOpen, setIsColumnSelectorOpen] = useState(false);

  const pageSizeOptions = useMemo(() => [25, 50, 100, 250], []);
  const {
    module: { selectedStoreId, token },
  } = useInventoryLayout();
  const [availabilityRecords, setAvailabilityRecords] = useState<
    Record<string, InventoryAvailabilityRecord>
  >({});
  const [availabilityTarget, setAvailabilityTarget] = useState<Device | null>(null);
  const [availabilityOpen, setAvailabilityOpen] = useState(false);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);

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

  const toggleRow = useCallback((id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleColumn = useCallback((id: ColumnId) => {
    setVisibleColumns((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleCloseAvailability = useCallback(() => {
    setAvailabilityOpen(false);
    setAvailabilityError(null);
  }, []);

  const handleOpenAvailability = useCallback(
    async (device: Device) => {
      const reference = buildAvailabilityReference(device);
      setAvailabilityTarget(device);
      setAvailabilityOpen(true);
      setAvailabilityError(null);
      if (availabilityRecords[reference]) {
        return;
      }
      setAvailabilityLoading(true);
      try {
        const response = await getInventoryAvailability(token, {
          ...(device.sku ? { skus: [device.sku] } : {}),
          ...(device.sku ? {} : { deviceIds: [device.id] }),
          limit: 10,
        });
        const mapped: Record<string, InventoryAvailabilityRecord> = {};
        response.items.forEach((item) => {
          mapped[item.reference] = item;
        });
        setAvailabilityRecords((prev) => ({ ...prev, ...mapped }));
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "No fue posible consultar la disponibilidad corporativa.";
        setAvailabilityError(message);
      } finally {
        setAvailabilityLoading(false);
      }
    },
    [availabilityRecords, token],
  );

  const handlePrintLabel = useCallback(
    async (device: Device) => {
      const qrPayload = JSON.stringify({
        sku: device.sku,
        imei: device.imei ?? null,
        serial: device.serial ?? null,
      });

      let dataUrl: string;
      try {
        dataUrl = await QRCode.toDataURL(qrPayload, {
          width: 160,
          margin: 1,
          errorCorrectionLevel: "M",
        });
      } catch (error) {
        emitClientError("No fue posible generar el código QR", error);
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
        <img loading="lazy" decoding="async"
          src="${dataUrl}"
          alt="QR del dispositivo"
        />
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
    },
    [escapeHtml],
  );

  const activeReference = availabilityTarget
    ? buildAvailabilityReference(availabilityTarget)
    : null;
  const activeAvailability = activeReference ? availabilityRecords[activeReference] : undefined;
  const availabilityModalTitle = availabilityTarget
    ? `Disponibilidad corporativa — ${availabilityTarget.name}`
    : "Disponibilidad corporativa";
  const availabilityModalSubtitle = availabilityTarget?.sku
    ? `SKU ${availabilityTarget.sku}`
    : "Consulta existencias por sucursal";

  const renderCell = (columnId: ColumnId, device: Device) => {
    switch (columnId) {
      case "expand":
        return (
          <button
            type="button"
            className="btn-icon-ghost"
            onClick={(e) => {
              e.stopPropagation();
              toggleRow(device.id);
            }}
            aria-label={expandedRows.has(device.id) ? "Contraer fila" : "Expandir fila"}
          >
            {expandedRows.has(device.id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
        );
      case "sku":
        return device.sku;
      case "name":
        return device.name;
      case "category":
        return device.categoria ?? "—";
      case "model":
        return device.modelo ?? "—";
      case "condition":
        return device.condicion ?? "—";
      case "status":
        return (
          <span className={`status-chip ${estadoTone(device.estado_comercial)}`}>
            {resolveEstadoLabel(device.estado_comercial)}
          </span>
        );
      case "inventory_status":
        return device.estado ?? "—";
      case "location":
        return device.ubicacion ?? "—";
      case "warehouse":
        return device.warehouse_name ?? "Default";
      case "stores": {
        const reference = buildAvailabilityReference(device);
        const availability = availabilityRecords[reference];
        return (
          <button
            type="button"
            className="inventory-availability__trigger"
            onClick={() => handleOpenAvailability(device)}
          >
            <MapPin aria-hidden="true" className="inventory-availability__trigger-icon" />
            <span>
              {availability ? `${availability.stores.length} sucursales` : "Ver existencias"}
            </span>
          </button>
        );
      }
      case "quantity":
        return device.quantity;
      case "cost":
        return device.costo_unitario != null ? formatCurrencyWithUsd(device.costo_unitario) : "—";
      case "price":
        return device.precio_venta != null
          ? formatCurrencyWithUsd(device.precio_venta)
          : device.unit_price != null
          ? formatCurrencyWithUsd(device.unit_price)
          : "—";
      case "total_value":
        return formatCurrencyWithUsd(device.inventory_value);
      case "actions":
        return (
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
              <button type="button" className="btn btn--ghost" onClick={() => onEditDevice(device)}>
                Editar ficha
              </button>
            ) : null}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <>
      <div className="inventory-table-controls">
        <div className="column-selector">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setIsColumnSelectorOpen(!isColumnSelectorOpen)}
          >
            <Columns size={16} />
            <span>Columnas</span>
          </button>
          {isColumnSelectorOpen && (
            <div className="column-selector__dropdown">
              <div className="column-selector__header">
                <h4>Personalizar vista</h4>
                <button
                  type="button"
                  className="btn-icon-ghost"
                  onClick={() => setIsColumnSelectorOpen(false)}
                >
                  ×
                </button>
              </div>
              <div className="column-selector__list">
                {COLUMNS.filter((col) => !col.alwaysVisible).map((col) => (
                  <label key={col.id} className="column-selector__item">
                    <input
                      type="checkbox"
                      checked={visibleColumns.has(col.id)}
                      onChange={() => toggleColumn(col.id)}
                    />
                    <span>{col.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <ScrollableTable
        items={devices}
        itemKey={(device) => device.id}
        pageSize={pageSize}
        renderHead={() => (
          <>
            {COLUMNS.filter((col) => visibleColumns.has(col.id)).map((col) => (
              <th key={col.id} scope="col" className={col.sticky ? `sticky-col-${col.sticky}` : ""}>
                {col.label}
              </th>
            ))}
          </>
        )}
        renderRow={(device) => {
          const isHighlighted = highlightedDeviceIds?.has(device.id);
          const isExpanded = expandedRows.has(device.id);

          return (
            <Fragment key={device.id}>
              <tr
                className={`${isHighlighted ? "inventory-row low-stock" : "inventory-row"} ${
                  isExpanded ? "expanded" : ""
                }`}
                onClick={() => toggleRow(device.id)}
              >
                {COLUMNS.filter((col) => visibleColumns.has(col.id)).map((col) => (
                  <td
                    key={col.id}
                    data-label={col.label}
                    className={col.sticky ? `sticky-col-${col.sticky}` : ""}
                  >
                    {renderCell(col.id, device)}
                  </td>
                ))}
              </tr>
              {isExpanded && (
                <tr className="inventory-row-detail">
                  <td colSpan={visibleColumns.size}>
                    <div className="detail-grid">
                      <div className="detail-section">
                        <h4>Identificadores</h4>
                        <div className="identifier-stack">
                          {device.imei ? <span>IMEI catálogo: {device.imei}</span> : null}
                          {device.serial ? <span>Serie catálogo: {device.serial}</span> : null}
                          {device.identifier?.imei_1 ? (
                            <span>IMEI 1: {device.identifier.imei_1}</span>
                          ) : null}
                          {device.identifier?.imei_2 ? (
                            <span>IMEI 2: {device.identifier.imei_2}</span>
                          ) : null}
                          {device.identifier?.numero_serie ? (
                            <span>Serie extendida: {device.identifier.numero_serie}</span>
                          ) : null}
                          {!device.imei &&
                          !device.serial &&
                          !device.identifier?.imei_1 &&
                          !device.identifier?.imei_2 &&
                          !device.identifier?.numero_serie ? (
                            <span className="muted-text">Sin identificadores registrados</span>
                          ) : null}
                        </div>
                      </div>
                      <div className="detail-section">
                        <h4>Detalles de inventario</h4>
                        <dl className="detail-list">
                          <dt>Ubicación:</dt>
                          <dd>{device.ubicacion ?? "—"}</dd>
                          <dt>Almacén:</dt>
                          <dd>{device.warehouse_name ?? "Default"}</dd>
                          <dt>Estado inventario:</dt>
                          <dd>{device.estado ?? "—"}</dd>
                          <dt>Estado técnico:</dt>
                          <dd>{device.identifier?.estado_tecnico ?? "—"}</dd>
                        </dl>
                      </div>
                      {device.identifier?.observaciones && (
                        <div className="detail-section full-width">
                          <h4>Notas</h4>
                          <p>{device.identifier.observaciones}</p>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        }}
        emptyMessage={emptyMessage ?? "No hay dispositivos registrados para esta sucursal."}
        title="Inventario corporativo"
        ariaLabel="Tabla de inventario corporativo"
        footer={
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
        }
      />
      <Modal
        open={availabilityOpen}
        onClose={handleCloseAvailability}
        title={availabilityModalTitle}
        description={availabilityModalSubtitle}
        size="md"
      >
        <div className="inventory-availability__content">
          {availabilityLoading ? (
            <p className="muted-text">Consultando existencias corporativas…</p>
          ) : null}
          {availabilityError ? (
            <p className="inventory-availability__error">{availabilityError}</p>
          ) : null}
          {!availabilityLoading && !availabilityError ? (
            activeAvailability ? (
              <>
                <table className="inventory-availability__table">
                  <thead>
                    <tr>
                      <th scope="col">Sucursal</th>
                      <th scope="col">Unidades</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeAvailability.stores.map((store) => {
                      const isCurrent =
                        typeof selectedStoreId === "number" && store.store_id === selectedStoreId;
                      const rowClassName = isCurrent
                        ? "inventory-availability__row inventory-availability__row--active"
                        : "inventory-availability__row";
                      return (
                        <tr key={store.store_id} className={rowClassName}>
                          <td>
                            <div className="inventory-availability__store">
                              <span>{store.store_name}</span>
                              {isCurrent ? (
                                <span className="inventory-availability__badge">
                                  Sucursal actual
                                </span>
                              ) : null}
                            </div>
                          </td>
                          <td className="inventory-availability__qty">{store.quantity}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="inventory-availability__footer">
                  <span className="inventory-availability__total">
                    Total corporativo: <strong>{activeAvailability.total_quantity}</strong> unidades
                  </span>
                </div>
              </>
            ) : (
              <p className="muted-text">
                Sin datos de otras sucursales registrados para este dispositivo.
              </p>
            )
          ) : null}
        </div>
      </Modal>
    </>
  );
}

export default InventoryTable;
