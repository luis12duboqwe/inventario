import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type {
  ContactHistoryEntry,
  Customer,
  CustomerDashboardMetrics,
  CustomerLedgerEntry,
  CustomerPortfolioReport,
  CustomerSummary,
} from "../../../api";
import {
  appendCustomerNote,
  createCustomer,
  deleteCustomer,
  exportCustomerPortfolioExcel,
  exportCustomerPortfolioPdf,
  exportCustomersCsv,
  getCustomerDashboardMetrics,
  getCustomerPortfolio,
  getCustomerSummary,
  listCustomers,
  registerCustomerPayment,
  updateCustomer,
} from "../../../api";
import type {
  CustomerFilters,
  CustomerFormState,
  DashboardFilters,
  LedgerEntryWithDetails,
  PortfolioFilters,
} from "../../../types/customers";

export const CUSTOMER_TYPES: { value: string; label: string }[] = [
  { value: "minorista", label: "Minorista" },
  { value: "mayorista", label: "Mayorista" },
  { value: "corporativo", label: "Corporativo" },
  { value: "vip", label: "VIP" },
];

export const CUSTOMER_STATUSES: { value: string; label: string }[] = [
  { value: "activo", label: "Activo" },
  { value: "inactivo", label: "Inactivo" },
  { value: "moroso", label: "Moroso" },
  { value: "bloqueado", label: "Bloqueado" },
  { value: "vip", label: "VIP" },
];

export const DEBT_FILTERS: { value: string; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "con_deuda", label: "Con saldo pendiente" },
  { value: "sin_deuda", label: "Sin saldo" },
];

export const LEDGER_LABELS: Record<CustomerLedgerEntry["entry_type"], string> = {
  sale: "Cargo por venta",
  payment: "Pago registrado",
  adjustment: "Ajuste manual",
  note: "Nota",
};

const initialFormState: CustomerFormState = {
  name: "",
  contactName: "",
  email: "",
  phone: "",
  address: "",
  customerType: "minorista",
  status: "activo",
  creditLimit: 0,
  outstandingDebt: 0,
  notes: "",
  historyNote: "",
};

const initialPortfolioFilters: PortfolioFilters = {
  category: "delinquent",
  limit: 10,
  dateFrom: "",
  dateTo: "",
};

const initialDashboardFilters: DashboardFilters = {
  months: 6,
  topLimit: 5,
};

const initialCustomerFilters: CustomerFilters = {
  search: "",
  status: "todos",
  customerType: "todos",
  debt: "todos",
};

const useReasonPrompt = (setError: (message: string | null) => void) => {
  return (promptMessage: string): string | null => {
    const reason = window.prompt(promptMessage, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };
};

const useBlobDownloader = () => {
  return (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
};

const formatCurrencyValue = (value: number): string => {
  return value.toLocaleString("es-MX", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const resolveLedgerDetails = (entry: CustomerLedgerEntry): LedgerEntryWithDetails => {
  if (!entry.details) {
    return entry;
  }
  const detailEntries = Object.entries(entry.details);
  if (detailEntries.length === 0) {
    return entry;
  }
  const [label, raw] = detailEntries[0];
  let value: string | undefined;
  if (typeof raw === "string") {
    value = raw;
  } else if (typeof raw === "number") {
    value = raw.toString();
  }
  return { ...entry, detailsLabel: label, detailsValue: value };
};

export type CustomersControllerParams = {
  token: string;
};

export const useCustomersController = ({ token }: CustomersControllerParams) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerFilters, setCustomerFilters] = useState<CustomerFilters>({
    ...initialCustomerFilters,
  });
  const [loadingCustomers, setLoadingCustomers] = useState(false);
  const [savingCustomer, setSavingCustomer] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [formState, setFormState] = useState<CustomerFormState>({
    ...initialFormState,
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(null);
  const [customerSummary, setCustomerSummary] = useState<CustomerSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [portfolioFilters, setPortfolioFilters] = useState<PortfolioFilters>({
    ...initialPortfolioFilters,
  });
  const [portfolio, setPortfolio] = useState<CustomerPortfolioReport | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [exportingPortfolio, setExportingPortfolio] = useState<"pdf" | "xlsx" | null>(null);

  const [dashboardMetrics, setDashboardMetrics] = useState<CustomerDashboardMetrics | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardFilters, setDashboardFilters] = useState<DashboardFilters>({
    ...initialDashboardFilters,
  });

  const askReason = useReasonPrompt(setError);
  const downloadBlob = useBlobDownloader();

  const selectedCustomer = useMemo(
    () =>
      selectedCustomerId
        ? customers.find((customer) => customer.id === selectedCustomerId) ?? null
        : null,
    [customers, selectedCustomerId],
  );

  const formatCurrency = useCallback((value: number) => formatCurrencyValue(value), []);
  const resolveDetails = useCallback((entry: CustomerLedgerEntry) => resolveLedgerDetails(entry), []);

  const handleCustomerFiltersChange = <K extends keyof CustomerFilters>(
    key: K,
    value: CustomerFilters[K],
  ) => {
    setCustomerFilters((current) => ({ ...current, [key]: value }));
  };

  const refreshCustomers = useCallback(
    async (queryOverride?: string) => {
      try {
        setLoadingCustomers(true);
        setError(null);
        const data = await listCustomers(token, {
          query: queryOverride,
          limit: 200,
          status: customerFilters.status !== "todos" ? customerFilters.status : undefined,
          customerType:
            customerFilters.customerType !== "todos" ? customerFilters.customerType : undefined,
          hasDebt:
            customerFilters.debt === "con_deuda"
              ? true
              : customerFilters.debt === "sin_deuda"
              ? false
              : undefined,
          statusFilter: customerFilters.status !== "todos" ? customerFilters.status : undefined,
          customerTypeFilter:
            customerFilters.customerType !== "todos" ? customerFilters.customerType : undefined,
        });
        setCustomers(data);
        if (selectedCustomerId) {
          const exists = data.some((customer) => customer.id === selectedCustomerId);
          if (!exists) {
            setSelectedCustomerId(null);
            setCustomerSummary(null);
          }
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "No fue posible cargar el listado de clientes.",
        );
      } finally {
        setLoadingCustomers(false);
      }
    },
    [
      token,
      customerFilters.customerType,
      customerFilters.debt,
      customerFilters.status,
      selectedCustomerId,
    ],
  );

  const refreshSummary = useCallback(
    async (customerId?: number | null) => {
      if (!customerId) {
        setCustomerSummary(null);
        return;
      }
      try {
        setSummaryLoading(true);
        setSummaryError(null);
        const data = await getCustomerSummary(token, customerId);
        setCustomerSummary(data);
      } catch (err) {
        setSummaryError(
          err instanceof Error ? err.message : "No fue posible cargar el resumen del cliente.",
        );
      } finally {
        setSummaryLoading(false);
      }
    },
    [token],
  );

  const refreshPortfolio = useCallback(async () => {
    try {
      setPortfolioLoading(true);
      setPortfolioError(null);
      const data = await getCustomerPortfolio(token, {
        category: portfolioFilters.category,
        limit: portfolioFilters.limit,
        dateFrom: portfolioFilters.dateFrom || undefined,
        dateTo: portfolioFilters.dateTo || undefined,
      });
      setPortfolio(data);
    } catch (err) {
      setPortfolioError(
        err instanceof Error ? err.message : "No fue posible obtener el portafolio de clientes.",
      );
    } finally {
      setPortfolioLoading(false);
    }
  }, [token, portfolioFilters]);

  const refreshDashboard = useCallback(async () => {
    try {
      setDashboardLoading(true);
      setDashboardError(null);
      const data = await getCustomerDashboardMetrics(token, dashboardFilters);
      setDashboardMetrics(data);
    } catch (err) {
      setDashboardError(
        err instanceof Error ? err.message : "No fue posible cargar el dashboard de clientes.",
      );
    } finally {
      setDashboardLoading(false);
    }
  }, [token, dashboardFilters]);

  useEffect(() => {
    void refreshCustomers();
  }, [refreshCustomers]);

  useEffect(() => {
    const trimmed = customerFilters.search.trim();
    const handler = window.setTimeout(() => {
      void refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    }, 350);
    return () => window.clearTimeout(handler);
  }, [customerFilters.search, refreshCustomers]);

  useEffect(() => {
    void refreshPortfolio();
  }, [refreshPortfolio]);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const resetForm = () => {
    setFormState({ ...initialFormState });
    setEditingId(null);
  };

  const handleFormStateChange = <K extends keyof CustomerFormState>(
    key: K,
    value: CustomerFormState[K],
  ) => {
    setFormState((current) => ({ ...current, [key]: value }));
  };

  const handleSelectCustomer = (customer: Customer) => {
    setSelectedCustomerId(customer.id);
    void refreshSummary(customer.id);
  };

  const handleEdit = (customer: Customer) => {
    setEditingId(customer.id);
    setFormState({
      name: customer.name,
      contactName: customer.contact_name ?? "",
      email: customer.email ?? "",
      phone: customer.phone,
      address: customer.address ?? "",
      customerType: customer.customer_type ?? "minorista",
      status: customer.status ?? "activo",
      creditLimit: Number(customer.credit_limit ?? 0),
      outstandingDebt: Number(customer.outstanding_debt ?? 0),
      notes: customer.notes ?? "",
      historyNote: "",
    });
  };

  const handleDelete = async (customer: Customer) => {
    if (!window.confirm(`¿Eliminar al cliente ${customer.name}?`)) {
      return;
    }
    const reason = askReason("Motivo corporativo para eliminar al cliente");
    if (!reason) {
      return;
    }
    try {
      setError(null);
      await deleteCustomer(token, customer.id, reason);
      setMessage("Cliente eliminado correctamente.");
      const trimmed = customerFilters.search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (editingId === customer.id) {
        resetForm();
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible eliminar al cliente seleccionado.",
      );
    }
  };

  const handleAddNote = async (customer: Customer) => {
    const note = window.prompt("Nueva nota de seguimiento", "");
    if (!note || !note.trim()) {
      return;
    }
    const reason = askReason("Motivo corporativo para registrar la nota");
    if (!reason) {
      return;
    }
    try {
      await appendCustomerNote(token, customer.id, note.trim(), reason);
      setMessage("Nota registrada correctamente.");
      const trimmed = customerFilters.search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (customer.id === selectedCustomerId) {
        void refreshSummary(customer.id);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible agregar la nota al cliente.",
      );
    }
  };

  const handleAdjustDebt = async (customer: Customer) => {
    const nextAmountRaw = window.prompt(
      "Nuevo saldo pendiente",
      formatCurrency(Number(customer.outstanding_debt ?? 0)),
    );
    if (nextAmountRaw === null) {
      return;
    }
    const parsed = Number(nextAmountRaw.replace(/[^0-9.-]/g, ""));
    if (!Number.isFinite(parsed) || parsed < 0) {
      setError("Indica un monto válido (mayor o igual a cero).");
      return;
    }
    const reason = askReason("Motivo corporativo para ajustar la deuda");
    if (!reason) {
      return;
    }
    try {
      await updateCustomer(
        token,
        customer.id,
        { outstanding_debt: Number(parsed.toFixed(2)) },
        reason,
      );
      setMessage("Saldo pendiente actualizado.");
      const trimmed = customerFilters.search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (customer.id === selectedCustomerId) {
        void refreshSummary(customer.id);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible actualizar el saldo pendiente.",
      );
    }
  };

  const handleRegisterPayment = async (customer: Customer) => {
    const amountRaw = window.prompt("Monto del pago", "0.00");
    if (amountRaw === null) {
      return;
    }
    const amount = Number(amountRaw);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Debes indicar un monto válido y mayor a cero.");
      return;
    }
    const method = window.prompt("Método de pago", "transferencia") ?? "manual";
    const reference = window.prompt("Referencia del pago (opcional)", "") ?? undefined;
    const note = window.prompt("Nota interna (opcional)", "") ?? undefined;
    const saleIdRaw = window.prompt("ID de venta asociada (opcional)", "");
    let saleId: number | undefined;
    if (saleIdRaw && saleIdRaw.trim().length > 0) {
      const parsedSaleId = Number(saleIdRaw);
      if (Number.isFinite(parsedSaleId) && parsedSaleId > 0) {
        saleId = parsedSaleId;
      }
    }
    const reason = askReason("Motivo corporativo para registrar el pago");
    if (!reason) {
      return;
    }
    try {
      await registerCustomerPayment(
        token,
        customer.id,
        {
          amount: Number(amount.toFixed(2)),
          method,
          reference,
          note,
          sale_id: saleId,
        },
        reason,
      );
      setMessage("Pago registrado correctamente.");
      const trimmed = customerFilters.search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (customer.id === selectedCustomerId) {
        void refreshSummary(customer.id);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No fue posible registrar el pago del cliente.",
      );
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.name.trim()) {
      setError("Indica un nombre válido para el cliente.");
      return;
    }
    if (!formState.phone.trim()) {
      setError("Indica un teléfono de contacto.");
      return;
    }
    const reason = askReason(
      editingId ? "Motivo corporativo para actualizar al cliente" : "Motivo corporativo para crear al cliente",
    );
    if (!reason) {
      return;
    }
    const payload = {
      name: formState.name.trim(),
      contact_name: formState.contactName.trim() || undefined,
      email: formState.email.trim() || undefined,
      phone: formState.phone.trim(),
      address: formState.address.trim() || undefined,
      customer_type: formState.customerType,
      status: formState.status,
      credit_limit: Number(formState.creditLimit ?? 0),
      outstanding_debt: Number(formState.outstandingDebt ?? 0),
      notes: formState.notes.trim() || undefined,
    };
    try {
      setSavingCustomer(true);
      setError(null);
      if (editingId) {
        await updateCustomer(token, editingId, payload, reason);
        setMessage("Cliente actualizado correctamente.");
      } else {
        await createCustomer(token, payload, reason);
        setMessage("Cliente registrado correctamente.");
      }
      resetForm();
      const trimmed = customerFilters.search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible registrar o actualizar la información del cliente.",
      );
    } finally {
      setSavingCustomer(false);
    }
  };

  const handleExportCsv = async () => {
    const reason = askReason("Motivo corporativo para exportar clientes");
    if (!reason) {
      return;
    }
    try {
      const blob = await exportCustomersCsv(token, customerFilters, reason);
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      downloadBlob(blob, `clientes_${timestamp}.csv`);
      setMessage("Exportación generada correctamente.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar los clientes.");
    }
  };

  const handlePortfolioFiltersChange = <K extends keyof PortfolioFilters>(
    key: K,
    value: PortfolioFilters[K],
  ) => {
    setPortfolioFilters((current) => ({ ...current, [key]: value }));
  };

  const handleDashboardFiltersChange = <K extends keyof DashboardFilters>(
    key: K,
    value: DashboardFilters[K],
  ) => {
    setDashboardFilters((current) => ({ ...current, [key]: value }));
  };

  const handleExportPortfolio = async (format: "pdf" | "xlsx") => {
    const reason = askReason(
      format === "pdf"
        ? "Motivo corporativo para exportar portafolio en PDF"
        : "Motivo corporativo para exportar portafolio en Excel",
    );
    if (!reason) {
      return;
    }
    try {
      setExportingPortfolio(format);
      const filters = {
        category: portfolioFilters.category,
        limit: portfolioFilters.limit,
        dateFrom: portfolioFilters.dateFrom || undefined,
        dateTo: portfolioFilters.dateTo || undefined,
      };
      const blob =
        format === "pdf"
          ? await exportCustomerPortfolioPdf(token, filters, reason)
          : await exportCustomerPortfolioExcel(token, filters, reason);
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const filename =
        format === "pdf"
          ? `portafolio_clientes_${timestamp}.pdf`
          : `portafolio_clientes_${timestamp}.xlsx`;
      downloadBlob(blob, filename);
      setMessage("Portafolio exportado correctamente.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar el portafolio.");
    } finally {
      setExportingPortfolio(null);
    }
  };

  const totalDebt = useMemo(() => {
    return customers.reduce((acc, customer) => acc + Number(customer.outstanding_debt ?? 0), 0);
  }, [customers]);

  const delinquentRatio = useMemo(() => {
    if (!dashboardMetrics || dashboardMetrics.total_customers === 0) {
      return 0;
    }
    return dashboardMetrics.delinquent_customers / dashboardMetrics.total_customers;
  }, [dashboardMetrics]);

  const customerNotes = useMemo(() => {
    if (!customerSummary?.customer?.notes) {
      return [] as string[];
    }
    return customerSummary.customer.notes
      .split(/\r?\n+/)
      .map((note) => note.trim())
      .filter((note) => note.length > 0);
  }, [customerSummary]);

  const customerHistory = useMemo(() => {
    if (!customerSummary?.customer?.history) {
      return [] as ContactHistoryEntry[];
    }
    return [...customerSummary.customer.history]
      .sort(
        (left, right) =>
          new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime(),
      )
      .slice(0, 6);
  }, [customerSummary]);

  const recentInvoices = useMemo(() => {
    if (!customerSummary?.invoices) {
      return [] as CustomerSummary["invoices"];
    }
    return [...customerSummary.invoices]
      .sort(
        (left, right) =>
          new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
      )
      .slice(0, 5);
  }, [customerSummary]);

  return {
    customers,
    customerFilters,
    loadingCustomers,
    savingCustomer,
    error,
    message,
    formState,
    editingId,
    selectedCustomer,
    selectedCustomerId,
    customerSummary,
    summaryLoading,
    summaryError,
    portfolio,
    portfolioFilters,
    portfolioLoading,
    portfolioError,
    exportingPortfolio,
    dashboardMetrics,
    dashboardFilters,
    dashboardLoading,
    dashboardError,
    totalDebt,
    delinquentRatio,
    customerNotes,
    customerHistory,
    recentInvoices,
    formatCurrency,
    resolveDetails,
    handleSubmit,
    handleFormStateChange,
    resetForm,
    handleExportCsv,
    handleCustomerFiltersChange,
    handleSelectCustomer,
    handleEdit,
    handleAddNote,
    handleRegisterPayment,
    handleAdjustDebt,
    handleDelete,
    handlePortfolioFiltersChange,
    refreshPortfolio,
    handleExportPortfolio,
    handleDashboardFiltersChange,
    refreshDashboard,
  } as const;
};

export type CustomersControllerState = ReturnType<typeof useCustomersController>;
