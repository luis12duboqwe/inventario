import { useCallback, useEffect, useMemo, useState } from "react";
import type { Customer, Device, PosConfig, Sale, Store, UserAccount } from "../../../api";
import {
  createSale,
  downloadPosReceipt,
  exportSalesExcel,
  exportSalesPdf,
  getDevices,
  getPosConfig,
  listCustomers,
  listSales,
  listUsers,
} from "../../../api";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

type SaleLine = {
  device: Device;
  quantity: number;
};

type SaleFormState = {
  storeId: number | null;
  paymentMethod: Sale["payment_method"];
  discountPercent: number;
  customerId: number | null;
  customerName: string;
  notes: string;
  reason: string;
};

type SalesFilterState = {
  storeId: number | null;
  customerId: number | null;
  userId: number | null;
  dateFrom: string;
  dateTo: string;
  query: string;
};

const paymentLabels: Record<Sale["payment_method"], string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  OTRO: "Otro",
  CREDITO: "Crédito",
};

const currencyFormatter = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

function Sales({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [saleForm, setSaleForm] = useState<SaleFormState>(
    () => ({
      storeId: defaultStoreId ?? null,
      paymentMethod: "EFECTIVO",
      discountPercent: 0,
      customerId: null,
      customerName: "",
      notes: "",
      reason: "Venta mostrador",
    })
  );
  const [saleItems, setSaleItems] = useState<SaleLine[]>([]);
  const [deviceQuery, setDeviceQuery] = useState<string>("");
  const [devices, setDevices] = useState<Device[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [sales, setSales] = useState<Sale[]>([]);
  const [filters, setFilters] = useState<SalesFilterState>({
    storeId: defaultStoreId ?? null,
    customerId: null,
    userId: null,
    dateFrom: "",
    dateTo: "",
    query: "",
  });
  const [posConfig, setPosConfig] = useState<PosConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [isPrinting, setIsPrinting] = useState<boolean>(false);
  const [isLoadingDevices, setIsLoadingDevices] = useState<boolean>(false);
  const [isLoadingSales, setIsLoadingSales] = useState<boolean>(false);
  const [exportReason, setExportReason] = useState<string>("Reporte ventas");
  const [lastSaleId, setLastSaleId] = useState<number | null>(null);

  const selectedCustomer = useMemo(
    () => customers.find((customer) => customer.id === saleForm.customerId) ?? null,
    [customers, saleForm.customerId]
  );

  const saleSummary = useMemo(() => {
    const gross = saleItems.reduce((total, line) => total + line.device.unit_price * line.quantity, 0);
    const discountPercent = Math.min(Math.max(saleForm.discountPercent, 0), 100);
    const discountAmount = gross * (discountPercent / 100);
    const subtotal = Math.max(0, gross - discountAmount);
    const taxRate = posConfig?.tax_rate ?? 0;
    const taxAmount = subtotal * (taxRate / 100);
    const total = subtotal + taxAmount;
    return {
      gross,
      discount: discountAmount,
      subtotal,
      taxAmount,
      total,
      taxRate,
    };
  }, [saleForm.discountPercent, posConfig?.tax_rate, saleItems]);

  const salesDashboard = useMemo(() => {
    const aggregate = sales.reduce(
      (acc, sale) => {
        acc.total += sale.total_amount;
        acc.subtotal += sale.subtotal_amount;
        acc.tax += sale.tax_amount;
        const dayKey = new Date(sale.created_at).toISOString().slice(0, 10);
        const current = acc.daily.get(dayKey) ?? { total: 0, count: 0 };
        current.total += sale.total_amount;
        current.count += 1;
        acc.daily.set(dayKey, current);
        return acc;
      },
      { total: 0, subtotal: 0, tax: 0, daily: new Map<string, { total: number; count: number }>() }
    );
    const totalSales = sales.length;
    const dailyStats = Array.from(aggregate.daily.entries())
      .map(([day, info]) => ({
        day,
        total: info.total,
        count: info.count,
        average: info.count > 0 ? info.total / info.count : 0,
      }))
      .sort((a, b) => (a.day < b.day ? 1 : -1));
    return {
      total: aggregate.total,
      subtotal: aggregate.subtotal,
      tax: aggregate.tax,
      count: totalSales,
      average: totalSales > 0 ? aggregate.total / totalSales : 0,
      dailyStats,
    };
  }, [sales]);

  useEffect(() => {
    const loadCustomers = async () => {
      try {
        const data = await listCustomers(token);
        setCustomers(data);
      } catch (err) {
        setError((err as Error).message ?? "No fue posible cargar clientes");
      }
    };
    const loadUsers = async () => {
      try {
        const data = await listUsers(token);
        setUsers(data);
      } catch (err) {
        setError((err as Error).message ?? "No fue posible cargar usuarios");
      }
    };
    loadCustomers();
    loadUsers();
  }, [token]);

  useEffect(() => {
    setSaleForm((current) => ({ ...current, storeId: defaultStoreId ?? null }));
    setFilters((current) => ({ ...current, storeId: defaultStoreId ?? null }));
  }, [defaultStoreId]);

  useEffect(() => {
    if (!saleForm.storeId) {
      setPosConfig(null);
      return;
    }
    let active = true;
    const loadConfig = async () => {
      try {
        const config = await getPosConfig(token, saleForm.storeId!);
        if (active) {
          setPosConfig(config);
        }
      } catch (err) {
        if (active) {
          setError((err as Error).message ?? "No fue posible cargar la configuración de POS");
        }
      }
    };
    loadConfig();
    return () => {
      active = false;
    };
  }, [saleForm.storeId, token]);

  useEffect(() => {
    setSaleItems([]);
    setDeviceQuery("");
  }, [saleForm.storeId]);

  useEffect(() => {
    if (!saleForm.storeId) {
      setDevices([]);
      setSaleItems([]);
      return;
    }
    let active = true;
    setIsLoadingDevices(true);
    const timeout = window.setTimeout(async () => {
      try {
        const data = await getDevices(token, saleForm.storeId!, {
          estado_inventario: "disponible",
          search: deviceQuery.trim() || undefined,
        });
        if (active) {
          setDevices(data);
        }
      } catch (err) {
        if (active) {
          setError((err as Error).message ?? "No fue posible cargar los dispositivos disponibles");
        }
      } finally {
        if (active) {
          setIsLoadingDevices(false);
        }
      }
    }, 350);
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [deviceQuery, saleForm.storeId, token]);

  const refreshSalesList = useCallback(async () => {
    setIsLoadingSales(true);
    try {
      const data = await listSales(token, {
        storeId: filters.storeId ?? undefined,
        customerId: filters.customerId ?? undefined,
        userId: filters.userId ?? undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        query: filters.query.trim() || undefined,
        limit: 200,
      });
      setSales(data);
    } catch (err) {
      setError((err as Error).message ?? "No fue posible cargar las ventas");
    } finally {
      setIsLoadingSales(false);
    }
  }, [filters.customerId, filters.dateFrom, filters.dateTo, filters.query, filters.storeId, filters.userId, token]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void refreshSalesList();
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [refreshSalesList]);

  const updateSaleForm = (updates: Partial<SaleFormState>) => {
    setSaleForm((current) => ({ ...current, ...updates }));
  };

  const updateFilters = (updates: Partial<SalesFilterState>) => {
    setFilters((current) => ({ ...current, ...updates }));
  };

  const handleAddDevice = (device: Device) => {
    setSaleItems((current) => {
      const existing = current.find((line) => line.device.id === device.id);
      if (existing) {
        return current.map((line) =>
          line.device.id === device.id
            ? { ...line, quantity: Math.min(device.quantity, line.quantity + 1) }
            : line
        );
      }
      return [...current, { device, quantity: 1 }];
    });
  };

  const handleQuantityChange = (deviceId: number, quantity: number) => {
    setSaleItems((current) =>
      current.map((line) =>
        line.device.id === deviceId
          ? { ...line, quantity: Math.max(1, Math.min(line.device.quantity, quantity)) }
          : line
      )
    );
  };

  const handleRemoveLine = (deviceId: number) => {
    setSaleItems((current) => current.filter((line) => line.device.id !== deviceId));
  };

  const resetSaleForm = () => {
    setSaleItems([]);
    setDeviceQuery("");
    setSaleForm((current) => ({
      ...current,
      discountPercent: 0,
      customerId: null,
      customerName: "",
      notes: "",
      reason: "Venta mostrador",
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!saleForm.storeId) {
      setError("Selecciona una sucursal para registrar la venta.");
      return;
    }
    if (saleItems.length === 0) {
      setError("Agrega al menos un dispositivo a la venta.");
      return;
    }
    if (!saleForm.reason.trim() || saleForm.reason.trim().length < 5) {
      setError("El motivo corporativo debe tener al menos 5 caracteres.");
      return;
    }
    const payloadItems = saleItems.map((line) => ({
      device_id: line.device.id,
      quantity: Math.max(1, line.quantity),
    }));
    const normalizedDiscount = Math.min(Math.max(saleForm.discountPercent, 0), 100);
    const customerName = saleForm.customerName.trim() || selectedCustomer?.name || undefined;
    setIsSaving(true);
    try {
      const sale = await createSale(
        token,
        {
          store_id: saleForm.storeId,
          payment_method: saleForm.paymentMethod,
          items: payloadItems,
          discount_percent: normalizedDiscount,
          customer_id: saleForm.customerId ?? undefined,
          customer_name: customerName,
          notes: saleForm.notes.trim() || undefined,
        },
        saleForm.reason.trim()
      );
      setError(null);
      setMessage("Venta registrada correctamente");
      setLastSaleId(sale.id);
      resetSaleForm();
      await refreshSalesList();
      onInventoryRefresh?.();
    } catch (err) {
      setError((err as Error).message ?? "No fue posible registrar la venta");
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = async (format: "pdf" | "xlsx") => {
    if (!exportReason.trim() || exportReason.trim().length < 5) {
      setError("El motivo corporativo para exportar debe tener al menos 5 caracteres.");
      return;
    }
    setIsExporting(true);
    try {
      const filtersPayload = {
        storeId: filters.storeId ?? undefined,
        customerId: filters.customerId ?? undefined,
        userId: filters.userId ?? undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
        query: filters.query.trim() || undefined,
      };
      const blob =
        format === "pdf"
          ? await exportSalesPdf(token, filtersPayload, exportReason.trim())
          : await exportSalesExcel(token, filtersPayload, exportReason.trim());
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ventas_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setError(null);
      setMessage(`Exportación ${format.toUpperCase()} generada correctamente`);
    } catch (err) {
      setError((err as Error).message ?? "No fue posible exportar las ventas");
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrintInvoice = async () => {
    if (!lastSaleId) {
      setError("Registra una venta antes de imprimir la factura.");
      return;
    }
    setIsPrinting(true);
    try {
      const blob = await downloadPosReceipt(token, lastSaleId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `venta_${lastSaleId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setMessage("Factura descargada correctamente");
      setError(null);
    } catch (err) {
      setError((err as Error).message ?? "No fue posible descargar la factura");
    } finally {
      setIsPrinting(false);
    }
  };

  return (
    <section className="card">
      <h2>Ventas y reportes</h2>
      <p className="card-subtitle">
        Registra ventas con búsqueda por IMEI/SKU/modelo, calcula impuestos y genera reportes corporativos.
      </p>
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}

      <form className="sales-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Sucursal
            <select
              value={saleForm.storeId ?? ""}
              onChange={(event) => updateSaleForm({ storeId: event.target.value ? Number(event.target.value) : null })}
            >
              <option value="">Selecciona una sucursal</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Cliente registrado
            <select
              value={saleForm.customerId ?? ""}
              onChange={(event) =>
                updateSaleForm({
                  customerId: event.target.value ? Number(event.target.value) : null,
                  customerName: "",
                })
              }
            >
              <option value="">Venta de mostrador</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Cliente manual (opcional)
            <input
              value={saleForm.customerName}
              onChange={(event) => updateSaleForm({ customerName: event.target.value, customerId: null })}
              placeholder="Nombre del cliente"
            />
          </label>

          <label>
            Método de pago
            <select
              value={saleForm.paymentMethod}
              onChange={(event) => updateSaleForm({ paymentMethod: event.target.value as Sale["payment_method"] })}
            >
              {Object.entries(paymentLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Descuento (%)
            <input
              type="number"
              min={0}
              max={100}
              value={saleForm.discountPercent}
              onChange={(event) => updateSaleForm({ discountPercent: Number(event.target.value) })}
            />
          </label>

          <label>
            Nota interna
            <input
              value={saleForm.notes}
              onChange={(event) => updateSaleForm({ notes: event.target.value })}
              placeholder="Observaciones"
            />
          </label>

          <label>
            Motivo corporativo
            <input
              value={saleForm.reason}
              onChange={(event) => updateSaleForm({ reason: event.target.value })}
              placeholder="Motivo para auditoría"
            />
          </label>

          <label className="span-2">
            Buscar dispositivo por IMEI, SKU o modelo
            <input
              value={deviceQuery}
              onChange={(event) => setDeviceQuery(event.target.value)}
              placeholder="Ej. 990000862471854 o FILTRO-1001"
              disabled={!saleForm.storeId}
            />
          </label>
        </div>

        <div className="section-divider">
          <h3>Dispositivos disponibles</h3>
          {!saleForm.storeId ? (
            <p className="muted-text">Selecciona una sucursal para consultar su inventario disponible.</p>
          ) : isLoadingDevices ? (
            <p className="muted-text">Cargando dispositivos disponibles...</p>
          ) : devices.length === 0 ? (
            <p className="muted-text">No se encontraron dispositivos disponibles con el criterio indicado.</p>
          ) : (
            <div className="table-responsive">
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Modelo</th>
                    <th>Precio</th>
                    <th>Existencias</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {devices.map((device) => (
                    <tr key={device.id}>
                      <td>{device.sku}</td>
                      <td>{device.name}</td>
                      <td>{currencyFormatter.format(device.unit_price)}</td>
                      <td>{device.quantity}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn--secondary"
                          onClick={() => handleAddDevice(device)}
                          disabled={device.quantity === 0}
                        >
                          Agregar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="section-divider">
          <h3>Carrito de venta</h3>
          {saleItems.length === 0 ? (
            <p className="muted-text">Agrega dispositivos para calcular el total de la venta.</p>
          ) : (
            <div className="table-responsive">
              <table>
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Descripción</th>
                    <th>Cantidad</th>
                    <th>Precio unitario</th>
                    <th>Total línea</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {saleItems.map((line) => (
                    <tr key={line.device.id}>
                      <td>{line.device.sku}</td>
                      <td>{line.device.name}</td>
                      <td>
                        <input
                          type="number"
                          min={1}
                          max={line.device.quantity}
                          value={line.quantity}
                          onChange={(event) => handleQuantityChange(line.device.id, Number(event.target.value))}
                        />
                      </td>
                      <td>{currencyFormatter.format(line.device.unit_price)}</td>
                      <td>{currencyFormatter.format(line.device.unit_price * line.quantity)}</td>
                      <td>
                        <button type="button" className="btn btn--ghost" onClick={() => handleRemoveLine(line.device.id)}>
                          Quitar
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="totals-grid">
            <div className="totals-card">
              <h4>Resumen</h4>
              <ul className="compact-list">
                <li>Total bruto: {currencyFormatter.format(saleSummary.gross)}</li>
                <li>Descuento: {currencyFormatter.format(saleSummary.discount)}</li>
                <li>Subtotal: {currencyFormatter.format(saleSummary.subtotal)}</li>
                <li>
                  Impuesto ({saleSummary.taxRate.toFixed(2)}%): {currencyFormatter.format(saleSummary.taxAmount)}
                </li>
                <li className="highlight">Total a cobrar: {currencyFormatter.format(saleSummary.total)}</li>
              </ul>
            </div>
            <div className="actions-card">
              <button type="submit" className="btn btn--primary" disabled={isSaving}>
                {isSaving ? "Guardando..." : "Guardar venta"}
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={handlePrintInvoice}
                disabled={!lastSaleId || isPrinting}
              >
                {isPrinting ? "Generando factura..." : "Imprimir factura"}
              </button>
              <button type="button" className="btn btn--ghost" onClick={resetSaleForm}>
                Limpiar formulario
              </button>
            </div>
          </div>
        </div>
      </form>

      <div className="section-divider">
        <h3>Resumen diario</h3>
        {salesDashboard.count === 0 ? (
          <p className="muted-text">Aún no hay ventas registradas para mostrar estadísticas.</p>
        ) : (
          <div className="metric-cards">
            <article className="metric-card metric-info">
              <h4>Ventas netas</h4>
              <p className="metric-value">{currencyFormatter.format(salesDashboard.total)}</p>
              <p className="metric-caption">{salesDashboard.count} operaciones registradas</p>
            </article>
            <article className="metric-card metric-secondary">
              <h4>Impuestos generados</h4>
              <p className="metric-value">{currencyFormatter.format(salesDashboard.tax)}</p>
              <p className="metric-caption">Subtotal {currencyFormatter.format(salesDashboard.subtotal)}</p>
            </article>
            <article className="metric-card metric-primary">
              <h4>Ticket promedio</h4>
              <p className="metric-value">{currencyFormatter.format(salesDashboard.average)}</p>
              <p className="metric-caption">Calculado sobre {salesDashboard.count} ventas</p>
            </article>
          </div>
        )}
        {salesDashboard.dailyStats.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Día</th>
                  <th>Total vendido</th>
                  <th>Operaciones</th>
                  <th>Ticket promedio</th>
                </tr>
              </thead>
              <tbody>
                {salesDashboard.dailyStats.map((entry) => (
                  <tr key={entry.day}>
                    <td>{entry.day}</td>
                    <td>{currencyFormatter.format(entry.total)}</td>
                    <td>{entry.count}</td>
                    <td>{currencyFormatter.format(entry.average)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="section-divider">
        <h3>Listado general de ventas</h3>
        <div className="form-grid">
          <label>
            Sucursal
            <select
              value={filters.storeId ?? ""}
              onChange={(event) => updateFilters({ storeId: event.target.value ? Number(event.target.value) : null })}
            >
              <option value="">Todas las sucursales</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Cliente
            <select
              value={filters.customerId ?? ""}
              onChange={(event) => updateFilters({ customerId: event.target.value ? Number(event.target.value) : null })}
            >
              <option value="">Todos los clientes</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Usuario
            <select
              value={filters.userId ?? ""}
              onChange={(event) => updateFilters({ userId: event.target.value ? Number(event.target.value) : null })}
            >
              <option value="">Todos los usuarios</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name ?? user.username}
                </option>
              ))}
            </select>
          </label>

          <label>
            Desde
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(event) => updateFilters({ dateFrom: event.target.value })}
            />
          </label>

          <label>
            Hasta
            <input
              type="date"
              value={filters.dateTo}
              onChange={(event) => updateFilters({ dateTo: event.target.value })}
            />
          </label>

          <label className="span-2">
            Buscar por IMEI, SKU o modelo
            <input
              value={filters.query}
              onChange={(event) => updateFilters({ query: event.target.value })}
              placeholder="Ej. IMEI, SKU, modelo o palabra clave"
            />
          </label>
        </div>

        <div className="form-grid">
          <label className="span-2">
            Motivo corporativo para exportar
            <input
              value={exportReason}
              onChange={(event) => setExportReason(event.target.value)}
              placeholder="Ej. Reporte diario ventas"
            />
          </label>
          <div className="button-row">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => handleExport("pdf")}
              disabled={isExporting}
            >
              {isExporting ? "Generando..." : "Exportar PDF"}
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => handleExport("xlsx")}
              disabled={isExporting}
            >
              {isExporting ? "Generando..." : "Exportar Excel"}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() =>
                setFilters({ storeId: null, customerId: null, userId: null, dateFrom: "", dateTo: "", query: "" })
              }
            >
              Limpiar filtros
            </button>
          </div>
        </div>

        {isLoadingSales ? (
          <p className="muted-text">Cargando ventas registradas...</p>
        ) : sales.length === 0 ? (
          <p className="muted-text">No hay ventas que coincidan con los filtros seleccionados.</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha</th>
                  <th>Sucursal</th>
                  <th>Cliente</th>
                  <th>Usuario</th>
                  <th>Método</th>
                  <th>Subtotal</th>
                  <th>Impuesto</th>
                  <th>Total</th>
                  <th>Artículos</th>
                </tr>
              </thead>
              <tbody>
                {sales.map((sale) => (
                  <tr key={sale.id}>
                    <td>#{sale.id}</td>
                    <td>{new Date(sale.created_at).toLocaleString("es-MX")}</td>
                    <td>{sale.store?.name ?? `Sucursal #${sale.store_id}`}</td>
                    <td>{sale.customer_name ?? "Mostrador"}</td>
                    <td>{sale.performed_by?.full_name ?? sale.performed_by?.username ?? "—"}</td>
                    <td>{paymentLabels[sale.payment_method]}</td>
                    <td>{currencyFormatter.format(sale.subtotal_amount)}</td>
                    <td>{currencyFormatter.format(sale.tax_amount)}</td>
                    <td>{currencyFormatter.format(sale.total_amount)}</td>
                    <td>
                      <ul className="compact-list">
                        {sale.items.map((item) => (
                          <li key={item.id}>
                            {item.device?.sku ?? `ID ${item.device_id}`} · {item.quantity} uds — {currencyFormatter.format(item.total_line)}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

export default Sales;
