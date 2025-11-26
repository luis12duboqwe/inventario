import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  Customer,
  Device,
  PosConfig,
  Sale,
  SaleCreateInput,
  Store,
  UserAccount,
} from "../../../api";
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
import FiltersPanel from "../../../pages/ventas/components/FiltersPanel";
import InvoiceModal from "../../../pages/ventas/components/InvoiceModal";
import SalesTable from "../../../pages/ventas/components/SalesTable";
import SidePanel from "../../../pages/ventas/components/SidePanel";
import SummaryCards from "../../../pages/ventas/components/SummaryCards";
import Toolbar from "../../../pages/ventas/components/Toolbar";
import type {
  SaleFormState,
  SaleLine,
  SaleSummary,
  SalesDashboard,
  SalesFilterState,
} from "../../../pages/ventas/components/types";

type Props = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
  onInventoryRefresh?: () => void;
};

const paymentLabels: Record<Sale["payment_method"], string> = {
  EFECTIVO: "Efectivo",
  TARJETA: "Tarjeta",
  TRANSFERENCIA: "Transferencia",
  OTRO: "Otro",
  CREDITO: "Crédito",
};

const currencyFormatter = new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" });

function Sales({ token, stores, defaultStoreId = null, onInventoryRefresh }: Props) {
  const [saleForm, setSaleForm] = useState<SaleFormState>(() => ({
    storeId: defaultStoreId ?? null,
    paymentMethod: "EFECTIVO",
    discountPercent: 0,
    customerId: null,
    customerName: "",
    notes: "",
    reason: "Venta mostrador",
  }));
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
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false);
  const [lastSaleSnapshot, setLastSaleSnapshot] = useState<{
    items: SaleLine[];
    summary: SaleSummary;
  } | null>(null);

  const selectedCustomer = useMemo(
    () => customers.find((customer) => customer.id === saleForm.customerId) ?? null,
    [customers, saleForm.customerId],
  );

  const saleSummary = useMemo<SaleSummary>(() => {
    const gross = saleItems.reduce(
      (total, line) => total + line.device.unit_price * line.quantity,
      0,
    );
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

  const salesDashboard = useMemo<SalesDashboard>(() => {
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
      { total: 0, subtotal: 0, tax: 0, daily: new Map<string, { total: number; count: number }>() },
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
        const searchTerm = deviceQuery.trim();
        const deviceFilters = {
          estado_inventario: "disponible" as const,
          ...(searchTerm ? { search: searchTerm } : {}),
        };
        const data = await getDevices(token, saleForm.storeId!, deviceFilters);
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
      const trimmedQuery = filters.query.trim();
      const filtersPayload = {
        ...(typeof filters.storeId === "number" ? { storeId: filters.storeId } : {}),
        ...(typeof filters.customerId === "number" ? { customerId: filters.customerId } : {}),
        ...(typeof filters.userId === "number" ? { userId: filters.userId } : {}),
        ...(filters.dateFrom ? { dateFrom: filters.dateFrom } : {}),
        ...(filters.dateTo ? { dateTo: filters.dateTo } : {}),
        ...(trimmedQuery ? { query: trimmedQuery } : {}),
        limit: 200,
      } as const;
      const data = await listSales(token, filtersPayload);
      setSales(data);
    } catch (err) {
      setError((err as Error).message ?? "No fue posible cargar las ventas");
    } finally {
      setIsLoadingSales(false);
    }
  }, [
    filters.customerId,
    filters.dateFrom,
    filters.dateTo,
    filters.query,
    filters.storeId,
    filters.userId,
    token,
  ]);

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
            : line,
        );
      }
      return [...current, { device, quantity: 1, batchCode: device.lote ?? "" }];
    });
  };

  const handleQuantityChange = (deviceId: number, quantity: number) => {
    setSaleItems((current) =>
      current.map((line) =>
        line.device.id === deviceId
          ? { ...line, quantity: Math.max(1, Math.min(line.device.quantity, quantity)) }
          : line,
      ),
    );
  };

  const handleBatchCodeChange = (deviceId: number, batchCode: string) => {
    setSaleItems((current) =>
      current.map((line) => (line.device.id === deviceId ? { ...line, batchCode } : line)),
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
    const payloadItems = saleItems.map((line) => {
      const entry: SaleCreateInput["items"][number] = {
        device_id: line.device.id,
        quantity: Math.max(1, line.quantity),
      };
      const normalizedBatch = line.batchCode.trim();
      if (normalizedBatch) {
        entry.batch_code = normalizedBatch;
      }
      return entry;
    });
    const normalizedDiscount = Math.min(Math.max(saleForm.discountPercent, 0), 100);
    const customerName = saleForm.customerName.trim() || selectedCustomer?.name || "";
    const payload: SaleCreateInput = {
      store_id: saleForm.storeId,
      payment_method: saleForm.paymentMethod,
      items: payloadItems,
      discount_percent: normalizedDiscount,
    };
    if (saleForm.customerId !== null && saleForm.customerId !== undefined) {
      payload.customer_id = saleForm.customerId;
    }
    if (customerName) {
      payload.customer_name = customerName;
    }
    const notes = saleForm.notes.trim();
    if (notes) {
      payload.notes = notes;
    }
    setIsSaving(true);
    try {
      const sale = await createSale(token, payload, saleForm.reason.trim());
      setError(null);
      setMessage("Venta registrada correctamente");
      setLastSaleId(sale.id);
      setLastSaleSnapshot({
        items: saleItems.map((line) => ({
          device: line.device,
          quantity: line.quantity,
          batchCode: line.batchCode,
        })),
        summary: saleSummary,
      });
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
      const trimmedQuery = filters.query.trim();
      const filtersPayload = {
        ...(typeof filters.storeId === "number" ? { storeId: filters.storeId } : {}),
        ...(typeof filters.customerId === "number" ? { customerId: filters.customerId } : {}),
        ...(typeof filters.userId === "number" ? { userId: filters.userId } : {}),
        ...(filters.dateFrom ? { dateFrom: filters.dateFrom } : {}),
        ...(filters.dateTo ? { dateTo: filters.dateTo } : {}),
        ...(trimmedQuery ? { query: trimmedQuery } : {}),
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

  const handleOpenInvoiceModal = () => {
    if (!lastSaleId) {
      setError("Registra una venta antes de imprimir la factura.");
      return;
    }
    setError(null);
    setInvoiceModalOpen(true);
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
      setInvoiceModalOpen(false);
    } catch (err) {
      setError((err as Error).message ?? "No fue posible descargar la factura");
    } finally {
      setIsPrinting(false);
    }
  };

  return (
    <>
      <Toolbar
        title="Ventas y reportes"
        subtitle="Registra ventas con búsqueda por IMEI/SKU/modelo, calcula impuestos y genera reportes corporativos."
        message={message}
        error={error}
      >
        <SidePanel
          stores={stores}
          customers={customers}
          saleForm={saleForm}
          onSaleFormChange={updateSaleForm}
          deviceQuery={deviceQuery}
          onDeviceQueryChange={setDeviceQuery}
          devices={devices}
          isLoadingDevices={isLoadingDevices}
          onAddDevice={handleAddDevice}
          saleItems={saleItems}
          onQuantityChange={handleQuantityChange}
          onBatchCodeChange={handleBatchCodeChange}
          onRemoveLine={handleRemoveLine}
          saleSummary={saleSummary}
          paymentLabels={paymentLabels}
          isSaving={isSaving}
          isPrinting={isPrinting}
          onSubmit={handleSubmit}
          onReset={resetSaleForm}
          onRequestInvoice={handleOpenInvoiceModal}
          formatCurrency={(value) => currencyFormatter.format(value)}
          invoiceAvailable={Boolean(lastSaleId)}
        />
        <SummaryCards
          dashboard={salesDashboard}
          formatCurrency={(value) => currencyFormatter.format(value)}
        />
        <FiltersPanel
          stores={stores}
          customers={customers}
          users={users}
          filters={filters}
          exportReason={exportReason}
          isExporting={isExporting}
          onFiltersChange={updateFilters}
          onExportReasonChange={setExportReason}
          onExportPdf={() => handleExport("pdf")}
          onExportExcel={() => handleExport("xlsx")}
          onClearFilters={() =>
            setFilters({
              storeId: null,
              customerId: null,
              userId: null,
              dateFrom: "",
              dateTo: "",
              query: "",
            })
          }
        />
        <SalesTable
          sales={sales}
          isLoading={isLoadingSales}
          formatCurrency={(value) => currencyFormatter.format(value)}
          data-testid="quotes-list"
        />
      </Toolbar>
      <InvoiceModal
        open={invoiceModalOpen}
        saleId={lastSaleId}
        summary={lastSaleSnapshot?.summary ?? saleSummary}
        items={lastSaleSnapshot?.items ?? saleItems}
        onConfirm={handlePrintInvoice}
        onClose={() => setInvoiceModalOpen(false)}
        isProcessing={isPrinting}
      />
    </>
  );
}

export default Sales;
