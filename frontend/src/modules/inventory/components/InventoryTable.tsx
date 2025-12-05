import { ChangeEvent, useCallback, useMemo, useState, Fragment } from "react";
import { MapPin, ChevronDown, ChevronRight, Columns, CheckSquare, Square } from "lucide-react";

import ScrollableTable from "@shared/components/ScrollableTable";
import Modal from "@components/ui/Modal";
import { Device } from "@api/inventory";
import "./InventoryTable.css";
import { useInventoryLayout } from "../pages/context/InventoryLayoutContext";
import { formatCurrencyWithUsd } from "@/utils/locale";
import {
  useInventoryAvailability,
  buildAvailabilityReference,
} from "../hooks/useInventoryAvailability";
import { useLabelPrinter } from "../hooks/useLabelPrinter";
import PrintLabelDialog, { PrintOptions } from "./PrintLabelDialog";
import BulkTransferDialog from "./BulkTransferDialog";
import BulkStatusDialog from "./BulkStatusDialog";

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

type ColumnId =
  | "select"
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
  { id: "select", label: "", sticky: "left", alwaysVisible: true },
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
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<Set<number>>(new Set());
  const [visibleColumns, setVisibleColumns] = useState<Set<ColumnId>>(() => {
    return new Set(COLUMNS.filter((c) => !c.defaultHidden).map((c) => c.id));
  });
  const [isColumnSelectorOpen, setIsColumnSelectorOpen] = useState(false);

  // Print Dialog State
  const [isPrintDialogOpen, setIsPrintDialogOpen] = useState(false);
  const [devicesToPrint, setDevicesToPrint] = useState<Device[]>([]);

  // Transfer Dialog State
  const [isTransferDialogOpen, setIsTransferDialogOpen] = useState(false);

  // Status Dialog State
  const [isStatusDialogOpen, setIsStatusDialogOpen] = useState(false);

  const pageSizeOptions = useMemo(() => [25, 50, 100, 250], []);
  const {
    module: { selectedStoreId, token, stores },
    downloads: { triggerRefreshSummary },
  } = useInventoryLayout();

  const {
    availabilityRecords,
    availabilityTarget,
    availabilityOpen,
    availabilityLoading,
    availabilityError,
    handleOpenAvailability,
    handleCloseAvailability,
  } = useInventoryAvailability(token);

  const { handlePrintLabels } = useLabelPrinter();

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

  const toggleSelection = useCallback((id: number) => {
    setSelectedDeviceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selectedDeviceIds.size === devices.length && devices.length > 0) {
      setSelectedDeviceIds(new Set());
    } else {
      setSelectedDeviceIds(new Set(devices.map((d) => d.id)));
    }
  }, [devices, selectedDeviceIds]);

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

  const openPrintDialog = (devicesList: Device[]) => {
    setDevicesToPrint(devicesList);
    setIsPrintDialogOpen(true);
  };

  const handleConfirmPrint = (options: PrintOptions) => {
    void handlePrintLabels(devicesToPrint, options);
    setIsPrintDialogOpen(false);
    setDevicesToPrint([]);

    // Si imprimimos desde la selección masiva, limpiamos la selección
    if (selectedDeviceIds.size > 0 && devicesToPrint.length > 1) {
      setSelectedDeviceIds(new Set());
    }
  };

  const handleTransferClick = () => {
    setIsTransferDialogOpen(true);
  };

  const handleTransferSuccess = () => {
    setSelectedDeviceIds(new Set());
    triggerRefreshSummary();
  };

  const handleStatusClick = () => {
    setIsStatusDialogOpen(true);
  };

  const handleStatusSuccess = () => {
    setSelectedDeviceIds(new Set());
    triggerRefreshSummary();
  };

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
      case "select":
        return (
          <button
            type="button"
            className="btn-icon-ghost"
            onClick={(e) => {
              e.stopPropagation();
              toggleSelection(device.id);
            }}
            aria-label={
              selectedDeviceIds.has(device.id) ? "Deseleccionar fila" : "Seleccionar fila"
            }
          >
            {selectedDeviceIds.has(device.id) ? (
              <CheckSquare size={16} className="text-accent" />
            ) : (
              <Square size={16} />
            )}
          </button>
        );
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
              onClick={() => openPrintDialog([device])}
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

      {selectedDeviceIds.size > 0 && (
        <div className="floating-actions-bar fixed bottom-8 left-1/2 -translate-x-1/2 bg-surface-raised p-4 rounded-lg shadow-lg flex items-center gap-6 z-50 border border-border-subtle">
          <span className="font-semibold">{selectedDeviceIds.size} seleccionados</span>
          <div className="actions-group flex gap-2">
            <button
              className="btn btn--secondary btn--sm"
              onClick={() => {
                const selectedDevices = devices.filter((d) => selectedDeviceIds.has(d.id));
                openPrintDialog(selectedDevices);
              }}
            >
              Imprimir etiquetas
            </button>
            <button className="btn btn--secondary btn--sm" onClick={handleTransferClick}>
              Transferir
            </button>
            <button className="btn btn--secondary btn--sm" onClick={handleStatusClick}>
              Cambiar estado
            </button>
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => setSelectedDeviceIds(new Set())}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      <ScrollableTable
        items={devices}
        itemKey={(device) => device.id}
        pageSize={pageSize}
        tableClassName="inventory-table"
        renderHead={() => (
          <>
            {COLUMNS.filter((col) => visibleColumns.has(col.id)).map((col) => (
              <th key={col.id} scope="col" className={col.sticky ? `sticky-col-${col.sticky}` : ""}>
                {col.id === "select" ? (
                  <button
                    type="button"
                    className="btn-icon-ghost"
                    onClick={toggleSelectAll}
                    aria-label="Seleccionar todo"
                  >
                    {selectedDeviceIds.size === devices.length && devices.length > 0 ? (
                      <CheckSquare size={16} className="text-accent" />
                    ) : (
                      <Square size={16} />
                    )}
                  </button>
                ) : (
                  col.label
                )}
              </th>
            ))}
          </>
        )}
        renderRow={(device) => {
          const isHighlighted = highlightedDeviceIds?.has(device.id);
          const isExpanded = expandedRows.has(device.id);
          const isSelected = selectedDeviceIds.has(device.id);

          return (
            <Fragment key={device.id}>
              <tr
                className={`${isHighlighted ? "inventory-row low-stock" : "inventory-row"} ${
                  isExpanded ? "expanded" : ""
                } ${isSelected ? "selected" : ""}`}
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
        isOpen={availabilityOpen}
        onClose={handleCloseAvailability}
        title={availabilityModalTitle}
        size="lg"
      >
        <div className="inventory-availability__content">
          <p className="muted-text">{availabilityModalSubtitle}</p>

          {availabilityLoading && <p>Cargando disponibilidad...</p>}
          {availabilityError && (
            <p className="inventory-availability__error">
              Error al cargar disponibilidad: {availabilityError}
            </p>
          )}

          {activeAvailability && (
            <>
              <table className="inventory-availability__table">
                <thead>
                  <tr>
                    <th>Sucursal</th>
                    <th className="text-right">Disponible</th>
                    <th className="text-right">Reservado</th>
                    <th className="text-right">En tránsito</th>
                  </tr>
                </thead>
                <tbody>
                  {activeAvailability.stores.map((store) => (
                    <tr
                      key={store.store_id}
                      className={
                        store.store_id === selectedStoreId
                          ? "inventory-availability__row--active"
                          : ""
                      }
                    >
                      <td>
                        <div className="inventory-availability__store">
                          <span>{store.store_name}</span>
                          {store.store_id === selectedStoreId && (
                            <span className="inventory-availability__badge">Actual</span>
                          )}
                        </div>
                      </td>
                      <td className="inventory-availability__qty">{store.quantity}</td>
                      <td className="inventory-availability__qty muted-text">0</td>
                      <td className="inventory-availability__qty muted-text">0</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="inventory-availability__footer">
                <div className="inventory-availability__total">
                  Total corporativo: <strong>{activeAvailability.total_quantity}</strong> unidades
                </div>
              </div>
            </>
          )}
        </div>
        <div className="modal-actions">
          <button type="button" className="btn btn--primary" onClick={handleCloseAvailability}>
            Cerrar
          </button>
        </div>
      </Modal>

      <PrintLabelDialog
        open={isPrintDialogOpen}
        onClose={() => setIsPrintDialogOpen(false)}
        onConfirm={handleConfirmPrint}
        deviceCount={devicesToPrint.length}
      />

      <BulkTransferDialog
        open={isTransferDialogOpen}
        onClose={() => setIsTransferDialogOpen(false)}
        selectedDeviceIds={Array.from(selectedDeviceIds)}
        stores={stores}
        currentStoreId={selectedStoreId}
        token={token}
        onSuccess={handleTransferSuccess}
      />

      <BulkStatusDialog
        open={isStatusDialogOpen}
        onClose={() => setIsStatusDialogOpen(false)}
        selectedDevices={devices.filter((d) => selectedDeviceIds.has(d.id))}
        token={token}
        onSuccess={handleStatusSuccess}
      />
    </>
  );
}

export default InventoryTable;
