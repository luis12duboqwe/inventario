import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import type {
  ContactHistoryEntry,
  Customer,
  CustomerDashboardMetrics,
  CustomerLedgerEntry,
  CustomerPortfolioItem,
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

type Props = {
  token: string;
};

type CustomerFormState = {
  name: string;
  contactName: string;
  email: string;
  phone: string;
  address: string;
  customerType: string;
  status: string;
  creditLimit: number;
  outstandingDebt: number;
  notes: string;
  historyNote: string;
};

type PortfolioFilters = {
  category: "delinquent" | "frequent";
  limit: number;
  dateFrom: string;
  dateTo: string;
};

type DashboardFilters = {
  months: number;
  topLimit: number;
};

type CustomerFilters = {
  search: string;
  status: string;
  customerType: string;
  debt: string;
};

type LedgerEntryWithDetails = CustomerLedgerEntry & {
  detailsLabel?: string;
  detailsValue?: string;
};

const CUSTOMER_TYPES: { value: string; label: string }[] = [
  { value: "minorista", label: "Minorista" },
  { value: "mayorista", label: "Mayorista" },
  { value: "corporativo", label: "Corporativo" },
  { value: "vip", label: "VIP" },
];

const CUSTOMER_STATUSES: { value: string; label: string }[] = [
  { value: "activo", label: "Activo" },
  { value: "inactivo", label: "Inactivo" },
  { value: "moroso", label: "Moroso" },
  { value: "bloqueado", label: "Bloqueado" },
  { value: "vip", label: "VIP" },
];

const DEBT_FILTERS: { value: string; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "con_deuda", label: "Con saldo pendiente" },
  { value: "sin_deuda", label: "Sin saldo" },
];

const LEDGER_LABELS: Record<CustomerLedgerEntry["entry_type"], string> = {
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

function formatCurrency(value: number): string {
  return value.toLocaleString("es-MX", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function resolveDetails(entry: CustomerLedgerEntry): LedgerEntryWithDetails {
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
}

function Customers({ token }: Props) {
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

  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(
    null,
  );
  const [customerSummary, setCustomerSummary] = useState<CustomerSummary | null>(
    null,
  );
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [portfolioFilters, setPortfolioFilters] = useState<PortfolioFilters>({
    ...initialPortfolioFilters,
  });
  const [portfolio, setPortfolio] =
    useState<CustomerPortfolioReport | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [exportingPortfolio, setExportingPortfolio] = useState<
    "pdf" | "xlsx" | null
  >(null);

  const [dashboardFilters, setDashboardFilters] =
    useState<DashboardFilters>(initialDashboardFilters);
  const [dashboardMetrics, setDashboardMetrics] =
    useState<CustomerDashboardMetrics | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const totalDebt = useMemo(
    () =>
      customers.reduce(
        (accumulator, customer) =>
          accumulator + (Number(customer.outstanding_debt) || 0),
        0,
      ),
    [customers],
  );

  const selectedCustomer = useMemo(
    () =>
      selectedCustomerId
        ? customers.find((customer) => customer.id === selectedCustomerId) ??
          null
        : null,
    [customers, selectedCustomerId],
  );

  const handleCustomerFiltersChange = <K extends keyof CustomerFilters>(
    key: K,
    value: CustomerFilters[K],
  ) => {
    setCustomerFilters((current) => ({ ...current, [key]: value }));
  };

  const askReason = useCallback(
    (promptMessage: string): string | null => {
      const reason = window.prompt(promptMessage, "");
      if (!reason || reason.trim().length < 5) {
        setError(
          "Debes indicar un motivo corporativo válido (mínimo 5 caracteres).",
        );
        return null;
      }
      return reason.trim();
    },
    [],
  );

  const refreshCustomers = useCallback(
    async (queryOverride?: string) => {
      try {
        setLoadingCustomers(true);
        setError(null);
        const data = await listCustomers(token, {
          query: queryOverride,
          limit: 200,
          status:
            customerFilters.status !== "todos"
              ? customerFilters.status
              : undefined,
          customerType:
            customerFilters.customerType !== "todos"
              ? customerFilters.customerType
              : undefined,
          hasDebt:
            customerFilters.debt === "con_deuda"
              ? true
              : customerFilters.debt === "sin_deuda"
              ? false
              : undefined,
          statusFilter:
            customerFilters.status !== "todos"
              ? customerFilters.status
              : undefined,
          customerTypeFilter:
            customerFilters.customerType !== "todos"
              ? customerFilters.customerType
              : undefined,
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
          err instanceof Error
            ? err.message
            : "No fue posible cargar el listado de clientes.",
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
    async (customerId: number) => {
      try {
        setSummaryLoading(true);
        setSummaryError(null);
        const summary = await getCustomerSummary(token, customerId);
        setCustomerSummary(summary);
      } catch (err) {
        setSummaryError(
          err instanceof Error
            ? err.message
            : "No fue posible obtener el perfil del cliente.",
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
      const params = {
        category: portfolioFilters.category,
        limit: portfolioFilters.limit,
        dateFrom: portfolioFilters.dateFrom || undefined,
        dateTo: portfolioFilters.dateTo || undefined,
      };
      const report = await getCustomerPortfolio(token, params);
      setPortfolio(report);
    } catch (err) {
      setPortfolioError(
        err instanceof Error
          ? err.message
          : "No fue posible generar el portafolio de clientes.",
      );
    } finally {
      setPortfolioLoading(false);
    }
  }, [token, portfolioFilters]);

  const refreshDashboard = useCallback(async () => {
    try {
      setDashboardLoading(true);
      setDashboardError(null);
      const metrics = await getCustomerDashboardMetrics(token, {
        months: dashboardFilters.months,
        topLimit: dashboardFilters.topLimit,
      });
      setDashboardMetrics(metrics);
    } catch (err) {
      setDashboardError(
        err instanceof Error
          ? err.message
          : "No fue posible cargar el dashboard de clientes.",
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

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.name.trim()) {
      setError("El nombre del cliente es obligatorio.");
      return;
    }
    if (!formState.phone.trim()) {
      setError("El teléfono del cliente es obligatorio.");
      return;
    }
    const reason = askReason(
      editingId
        ? "Motivo corporativo para actualizar al cliente"
        : "Motivo corporativo para registrar al cliente",
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
      credit_limit: Number.isFinite(formState.creditLimit)
        ? Math.max(0, Number(formState.creditLimit))
        : 0,
      notes: formState.notes.trim() || undefined,
      outstanding_debt: Number.isFinite(formState.outstandingDebt)
        ? Math.max(0, Number(formState.outstandingDebt))
        : undefined,
      history:
        formState.historyNote.trim().length > 0
          ? ([
              {
                timestamp: new Date().toISOString(),
                note: formState.historyNote.trim(),
              } satisfies ContactHistoryEntry,
            ] as ContactHistoryEntry[])
          : undefined,
    };

    try {
      setSavingCustomer(true);
      setError(null);
      setMessage(null);
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
          : "No fue posible guardar la información del cliente.",
      );
    } finally {
      setSavingCustomer(false);
    }
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
        err instanceof Error
          ? err.message
          : "No fue posible eliminar al cliente seleccionado.",
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
        err instanceof Error
          ? err.message
          : "No fue posible agregar la nota al cliente.",
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
    const parsed = Number(nextAmountRaw.replace(/[^0-9.\-]/g, ""));
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
        err instanceof Error
          ? err.message
          : "No fue posible actualizar el saldo pendiente.",
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
    const reference = window.prompt("Referencia del pago (opcional)", "") ??
      undefined;
    const note = window.prompt("Nota interna (opcional)", "") ?? undefined;
    const saleIdRaw = window.prompt("ID de venta asociada (opcional)", "");
    let saleId: number | undefined;
    if (saleIdRaw && saleIdRaw.trim().length > 0) {
      const parsed = Number(saleIdRaw);
      if (!Number.isFinite(parsed)) {
        setError("Indica un ID de venta válido.");
        return;
      }
      saleId = parsed;
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
          method: method.trim() || "manual",
          reference: reference?.trim() || undefined,
          note: note?.trim() || undefined,
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
        err instanceof Error
          ? err.message
          : "No fue posible registrar el pago.",
      );
    }
  };

  const handleSelectCustomer = (customer: Customer) => {
    setSelectedCustomerId(customer.id);
    setSummaryError(null);
    setCustomerSummary(null);
    void refreshSummary(customer.id);
  };

  const handleExportCsv = async () => {
    try {
      setError(null);
      const trimmed = customerFilters.search.trim();
      const blob = await exportCustomersCsv(token, {
        query: trimmed.length >= 2 ? trimmed : undefined,
        status:
          customerFilters.status !== "todos"
            ? customerFilters.status
            : undefined,
        customerType:
          customerFilters.customerType !== "todos"
            ? customerFilters.customerType
            : undefined,
        hasDebt:
          customerFilters.debt === "con_deuda"
            ? true
            : customerFilters.debt === "sin_deuda"
            ? false
            : undefined,
        statusFilter:
          customerFilters.status !== "todos"
            ? customerFilters.status
            : undefined,
        customerTypeFilter:
          customerFilters.customerType !== "todos"
            ? customerFilters.customerType
            : undefined,
      });
      downloadBlob(blob, "clientes.csv");
      setMessage("Exportación CSV generada correctamente.");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible exportar el listado de clientes.",
      );
    }
  };

  const handleExportPortfolio = async (format: "pdf" | "xlsx") => {
    const reason = askReason(
      `Motivo corporativo para descargar el portafolio (${format.toUpperCase()})`,
    );
    if (!reason) {
      return;
    }
    try {
      setExportingPortfolio(format);
      const params = {
        category: portfolioFilters.category,
        limit: portfolioFilters.limit,
        dateFrom: portfolioFilters.dateFrom || undefined,
        dateTo: portfolioFilters.dateTo || undefined,
      };
      const exporter =
        format === "pdf" ? exportCustomerPortfolioPdf : exportCustomerPortfolioExcel;
      const blob = await exporter(token, params, reason);
      downloadBlob(
        blob,
        `portafolio_clientes_${portfolioFilters.category}.${
          format === "pdf" ? "pdf" : "xlsx"
        }`,
      );
      setMessage("Reporte de clientes generado correctamente.");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No fue posible descargar el portafolio de clientes.",
      );
    } finally {
      setExportingPortfolio(null);
    }
  };

  const delinquentRatio = useMemo(() => {
    if (!dashboardMetrics || !dashboardMetrics.delinquent_summary) {
      return { percentage: 0, total: 0 };
    }
    const summary = dashboardMetrics.delinquent_summary;
    const base = summary.customers_with_debt || 0;
    if (base === 0) {
      return { percentage: 0, total: summary.total_outstanding_debt };
    }
    const percentage = summary.moroso_flagged
      ? Math.min(100, Math.round((summary.moroso_flagged / base) * 100))
      : 0;
    return { percentage, total: summary.total_outstanding_debt };
  }, [dashboardMetrics]);

  const newCustomersMaxValue = useMemo(() => {
    if (!dashboardMetrics?.new_customers_per_month?.length) {
      return 0;
    }
    return Math.max(
      ...dashboardMetrics.new_customers_per_month.map((point) => point.value),
    );
  }, [dashboardMetrics?.new_customers_per_month]);

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
          new Date(right.timestamp).getTime() -
          new Date(left.timestamp).getTime(),
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
          new Date(right.created_at).getTime() -
          new Date(left.created_at).getTime(),
      )
      .slice(0, 5);
  }, [customerSummary]);

  return (
    <section className="customers-module">
      {error ? <div className="alert error">{error}</div> : null}
      {message ? <div className="alert success">{message}</div> : null}

      <div className="panel">
        <div className="panel__header">
          <h2>Registro y actualización de clientes</h2>
          <p className="panel__subtitle">
            Mantén al día la información corporativa, el saldo pendiente y las notas
            de seguimiento de tus clientes.
          </p>
        </div>
        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            Nombre del cliente
            <input
              value={formState.name}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              placeholder="Ej. SuperCell Distribuciones"
              required
            />
          </label>
          <label>
            Contacto principal
            <input
              value={formState.contactName}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  contactName: event.target.value,
                }))
              }
              placeholder="Nombre del contacto"
            />
          </label>
          <label>
            Teléfono
            <input
              value={formState.phone}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  phone: event.target.value,
                }))
              }
              placeholder="10 dígitos"
              required
            />
          </label>
          <label>
            Correo electrónico
            <input
              type="email"
              value={formState.email}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
              placeholder="contacto@empresa.com"
            />
          </label>
          <label>
            Dirección
            <input
              value={formState.address}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  address: event.target.value,
                }))
              }
              placeholder="Calle, número y ciudad"
            />
          </label>
          <label>
            Tipo de cliente
            <select
              value={formState.customerType}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  customerType: event.target.value,
                }))
              }
            >
              {CUSTOMER_TYPES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Estado
            <select
              value={formState.status}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  status: event.target.value,
                }))
              }
            >
              {CUSTOMER_STATUSES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Límite de crédito (MXN)
            <input
              type="number"
              min={0}
              step="0.01"
              value={formState.creditLimit}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  creditLimit: Number(event.target.value),
                }))
              }
            />
          </label>
          <label>
            Saldo inicial (MXN)
            <input
              type="number"
              min={0}
              step="0.01"
              value={formState.outstandingDebt}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  outstandingDebt: Number(event.target.value),
                }))
              }
            />
          </label>
          <label className="span-2">
            Notas internas
            <textarea
              rows={2}
              value={formState.notes}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  notes: event.target.value,
                }))
              }
              placeholder="Instrucciones especiales, condiciones de crédito o preferencias"
            />
          </label>
          <label className="span-2">
            Nota para historial
            <textarea
              rows={2}
              value={formState.historyNote}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  historyNote: event.target.value,
                }))
              }
              placeholder="Se agregará al historial de contacto al guardar"
            />
          </label>
          <div className="actions-row">
            <button type="submit" className="btn btn--primary" disabled={savingCustomer}>
              {savingCustomer
                ? "Guardando..."
                : editingId
                ? "Actualizar cliente"
                : "Registrar cliente"}
            </button>
            {editingId ? (
              <button
                type="button"
                className="btn btn--ghost"
                onClick={resetForm}
                disabled={savingCustomer}
              >
                Cancelar edición
              </button>
            ) : null}
            <button
              type="button"
              className="btn btn--secondary"
              onClick={handleExportCsv}
              disabled={loadingCustomers}
            >
              Exportar CSV
            </button>
          </div>
        </form>
      </div>

      <div className="customers-columns">
        <div className="panel">
          <div className="panel__header">
            <h3>Listado de clientes</h3>
            <p className="panel__subtitle">
              Usa filtros combinados para ubicar clientes morosos, VIP o corporativos en
              segundos.
            </p>
          </div>
          <div className="form-grid">
            <label className="span-2">
              Búsqueda rápida
              <input
                value={customerFilters.search}
                onChange={(event) =>
                  handleCustomerFiltersChange("search", event.target.value)
                }
                placeholder="Nombre, correo, contacto o nota"
              />
              <span className="muted-text">
                Se actualiza automáticamente al escribir (mínimo 2 caracteres).
              </span>
            </label>
            <label>
              Estado
              <select
                value={customerFilters.status}
                onChange={(event) =>
                  handleCustomerFiltersChange("status", event.target.value)
                }
              >
                <option value="todos">Todos</option>
                {CUSTOMER_STATUSES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tipo
              <select
                value={customerFilters.customerType}
                onChange={(event) =>
                  handleCustomerFiltersChange("customerType", event.target.value)
                }
              >
                <option value="todos">Todos</option>
                {CUSTOMER_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Saldo pendiente
              <select
                value={customerFilters.debt}
                onChange={(event) =>
                  handleCustomerFiltersChange("debt", event.target.value)
                }
              >
                {DEBT_FILTERS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <span className="muted-text">Clientes encontrados</span>
              <strong>{customers.length}</strong>
            </div>
            <div>
              <span className="muted-text">Deuda consolidada</span>
              <strong>${formatCurrency(totalDebt)}</strong>
            </div>
          </div>

          {loadingCustomers ? (
            <p className="muted-text">Cargando clientes...</p>
          ) : customers.length === 0 ? (
            <p className="muted-text">
              No hay clientes que coincidan con los filtros seleccionados.
            </p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Contacto</th>
                    <th>Correo</th>
                    <th>Teléfono</th>
                    <th>Límite crédito</th>
                    <th>Saldo</th>
                    <th>Última interacción</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((customer) => {
                    const lastInteraction = customer.last_interaction_at
                      ? new Date(customer.last_interaction_at).toLocaleString("es-MX")
                      : "—";
                    const creditLimit = Number(customer.credit_limit ?? 0);
                    const debt = Number(customer.outstanding_debt ?? 0);
                    const statusClass =
                      customer.status === "moroso"
                        ? "badge warning"
                        : customer.status === "activo"
                        ? "badge success"
                        : "badge neutral";
                    return (
                      <tr
                        key={customer.id}
                        className={
                          selectedCustomerId === customer.id ? "is-selected" : undefined
                        }
                      >
                        <td>#{customer.id}</td>
                        <td>
                          <strong>{customer.name}</strong>
                          <div className="muted-text small">
                            Registrado el {" "}
                            {new Date(customer.created_at).toLocaleDateString("es-MX")}
                          </div>
                        </td>
                        <td>{customer.customer_type ?? "—"}</td>
                        <td>
                          <span className={statusClass}>{customer.status ?? "—"}</span>
                        </td>
                        <td>{customer.contact_name ?? "—"}</td>
                        <td>{customer.email ?? "—"}</td>
                        <td>{customer.phone}</td>
                        <td>${formatCurrency(creditLimit)}</td>
                        <td>${formatCurrency(debt)}</td>
                        <td>{lastInteraction}</td>
                        <td>
                          <div className="customer-actions">
                            <button
                              type="button"
                              className="btn btn--link"
                              onClick={() => handleSelectCustomer(customer)}
                            >
                              Perfil
                            </button>
                            <button
                              type="button"
                              className="btn btn--link"
                              onClick={() => handleEdit(customer)}
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              className="btn btn--link"
                              onClick={() => handleAddNote(customer)}
                            >
                              Nota
                            </button>
                            <button
                              type="button"
                              className="btn btn--link"
                              onClick={() => handleRegisterPayment(customer)}
                            >
                              Pago
                            </button>
                            <button
                              type="button"
                              className="btn btn--link"
                              onClick={() => handleAdjustDebt(customer)}
                            >
                              Ajustar saldo
                            </button>
                            <button
                              type="button"
                              className="btn btn--link"
                              onClick={() => handleDelete(customer)}
                            >
                              Eliminar
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel__header">
            <h3>Perfil financiero del cliente</h3>
            <p className="panel__subtitle">
              Consulta ventas, pagos, notas y el saldo disponible para tomar decisiones en
              el momento.
            </p>
          </div>

          {summaryLoading ? (
            <p className="muted-text">Cargando información del cliente...</p>
          ) : summaryError ? (
            <p className="error-text">{summaryError}</p>
          ) : customerSummary && selectedCustomer ? (
            <div className="customer-summary">
              <div className="summary-header">
                <div>
                  <h4>{customerSummary.customer.name}</h4>
                  <p className="muted-text">
                    Tipo {customerSummary.customer.customer_type} · Estado {" "}
                    {customerSummary.customer.status}
                  </p>
                </div>
                <div className="summary-financial">
                  <div>
                    <span className="muted-text">Saldo pendiente</span>
                    <strong>${formatCurrency(customerSummary.totals.outstanding_debt)}</strong>
                  </div>
                  <div>
                    <span className="muted-text">Crédito disponible</span>
                    <strong>${formatCurrency(customerSummary.totals.available_credit)}</strong>
                  </div>
                  <div>
                    <span className="muted-text">Límite</span>
                    <strong>${formatCurrency(customerSummary.totals.credit_limit)}</strong>
                  </div>
                </div>
              </div>

              <div className="summary-columns">
                <div>
                  <h5>Ventas recientes</h5>
                  {customerSummary.sales.length === 0 ? (
                    <p className="muted-text">Sin ventas registradas.</p>
                  ) : (
                    <ul className="summary-list">
                      {customerSummary.sales.slice(0, 5).map((sale) => (
                        <li key={sale.sale_id}>
                          <strong>Venta #{sale.sale_id}</strong>
                          <span className="muted-text">
                            {new Date(sale.created_at).toLocaleString("es-MX")} · {sale.status}
                          </span>
                          <span className="summary-amount">
                            Total ${formatCurrency(sale.total_amount)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h5>Pagos</h5>
                  {customerSummary.payments.length === 0 ? (
                    <p className="muted-text">Sin pagos recientes.</p>
                  ) : (
                    <ul className="summary-list">
                      {customerSummary.payments.slice(0, 5).map((payment) => (
                        <li key={payment.id}>
                          <div>
                            <strong>{LEDGER_LABELS[payment.entry_type]}</strong>
                            <span className="muted-text small">
                              {new Date(payment.created_at).toLocaleString("es-MX")}
                            </span>
                          </div>
                          <span className="summary-amount">
                            ${formatCurrency(payment.amount)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h5>Facturas emitidas</h5>
                  {recentInvoices.length === 0 ? (
                    <p className="muted-text">Sin facturas generadas.</p>
                  ) : (
                    <ul className="summary-list">
                      {recentInvoices.map((invoice) => (
                        <li key={invoice.invoice_number}>
                          <div>
                            <strong>{invoice.invoice_number}</strong>
                            <span className="muted-text small">
                              {new Date(invoice.created_at).toLocaleString("es-MX")}
                              {invoice.store_id ? ` · Sucursal ${invoice.store_id}` : ""}
                            </span>
                          </div>
                          <span className="summary-amount">
                            ${formatCurrency(invoice.total_amount)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h5>Notas y seguimiento</h5>
                  {customerNotes.length === 0 && customerHistory.length === 0 ? (
                    <p className="muted-text">Sin notas registradas.</p>
                  ) : (
                    <ul className="notes-stack">
                      {customerNotes.map((note, index) => (
                        <li key={`note-${index}`}>
                          <span className="note-chip">Nota interna</span>
                          <p>{note}</p>
                        </li>
                      ))}
                      {customerHistory.map((entry) => (
                        <li key={`history-${entry.timestamp}`}>
                          <span className="note-chip">
                            Seguimiento · {new Date(entry.timestamp).toLocaleString("es-MX")}
                          </span>
                          <p>{entry.note}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div>
                <h5>Historial de contacto</h5>
                {customerHistory.length === 0 ? (
                  <p className="muted-text">Sin interacciones registradas.</p>
                ) : (
                  <ul className="history-stack">
                    {customerHistory.map((entry) => (
                      <li key={`history-card-${entry.timestamp}`}>
                        <div>
                          <strong>{new Date(entry.timestamp).toLocaleString("es-MX")}</strong>
                          <span className="muted-text small">Bitácora de seguimiento</span>
                        </div>
                        <p>{entry.note}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h5>Bitácora reciente</h5>
                {customerSummary.ledger.length === 0 ? (
                  <p className="muted-text">Aún no hay movimientos registrados.</p>
                ) : (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Fecha</th>
                          <th>Tipo</th>
                          <th>Detalle</th>
                          <th>Monto</th>
                          <th>Saldo posterior</th>
                        </tr>
                      </thead>
                      <tbody>
                        {customerSummary.ledger.slice(0, 10).map((entry) => {
                          const enriched = resolveDetails(entry);
                          return (
                            <tr key={entry.id}>
                              <td>{new Date(entry.created_at).toLocaleString("es-MX")}</td>
                              <td>{LEDGER_LABELS[entry.entry_type]}</td>
                            <td>
                              {entry.note ?? enriched.detailsLabel ?? "—"}
                              {enriched.detailsValue ? (
                                <span className="muted-text"> · {enriched.detailsValue}</span>
                              ) : null}
                              {entry.created_by ? (
                                <span className="muted-text note-meta">
                                  · Registrado por {entry.created_by}
                                </span>
                              ) : null}
                            </td>
                            <td>${formatCurrency(entry.amount)}</td>
                            <td>${formatCurrency(entry.balance_after)}</td>
                          </tr>
                        );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p className="muted-text">
              Selecciona un cliente en el listado para visualizar su perfil financiero.
            </p>
          )}
        </div>
      </div>

      <div className="customers-dashboard">
        <div className="card">
          <div className="card-header">
            <div>
              <h3>Portafolio de clientes</h3>
              <p className="muted-text">
                Identifica clientes morosos o compradores frecuentes y exporta el reporte
                oficial con estilo oscuro.
              </p>
            </div>
            <div className="report-actions">
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => handleExportPortfolio("pdf")}
                disabled={exportingPortfolio === "pdf"}
              >
                {exportingPortfolio === "pdf" ? "Generando..." : "Exportar PDF"}
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => handleExportPortfolio("xlsx")}
                disabled={exportingPortfolio === "xlsx"}
              >
                {exportingPortfolio === "xlsx" ? "Generando..." : "Exportar Excel"}
              </button>
            </div>
          </div>

          <div className="form-grid">
            <label>
              Categoría
              <select
                value={portfolioFilters.category}
                onChange={(event) =>
                  setPortfolioFilters((current) => ({
                    ...current,
                    category: event.target.value as PortfolioFilters["category"],
                  }))
                }
              >
                <option value="delinquent">Clientes morosos</option>
                <option value="frequent">Compradores frecuentes</option>
              </select>
            </label>
            <label>
              Límite
              <input
                type="number"
                min={1}
                max={100}
                value={portfolioFilters.limit}
                onChange={(event) =>
                  setPortfolioFilters((current) => ({
                    ...current,
                    limit: Math.max(1, Number(event.target.value)),
                  }))
                }
              />
            </label>
            <label>
              Desde
              <input
                type="date"
                value={portfolioFilters.dateFrom}
                onChange={(event) =>
                  setPortfolioFilters((current) => ({
                    ...current,
                    dateFrom: event.target.value,
                  }))
                }
              />
            </label>
            <label>
              Hasta
              <input
                type="date"
                value={portfolioFilters.dateTo}
                onChange={(event) =>
                  setPortfolioFilters((current) => ({
                    ...current,
                    dateTo: event.target.value,
                  }))
                }
              />
            </label>
            <div>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => void refreshPortfolio()}
                disabled={portfolioLoading}
              >
                {portfolioLoading ? "Actualizando..." : "Actualizar vista"}
              </button>
            </div>
          </div>

          {portfolioLoading ? (
            <p className="muted-text">Generando portafolio...</p>
          ) : portfolioError ? (
            <p className="error-text">{portfolioError}</p>
          ) : portfolio ? (
            <>
              <div className="portfolio-summary">
                <div>
                  <span className="muted-text">Clientes listados</span>
                  <strong>{portfolio.totals.customers}</strong>
                </div>
                <div>
                  <span className="muted-text">Deuda total</span>
                  <strong>${formatCurrency(portfolio.totals.outstanding_debt)}</strong>
                </div>
                <div>
                  <span className="muted-text">Ventas acumuladas</span>
                  <strong>${formatCurrency(portfolio.totals.sales_total)}</strong>
                </div>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Tipo</th>
                      <th>Estado</th>
                      <th>Saldo</th>
                      <th>Ventas</th>
                      <th>Última compra</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.items.map((item: CustomerPortfolioItem) => (
                      <tr key={item.customer_id}>
                        <td>
                          <strong>{item.name}</strong>
                          <div className="muted-text">#{item.customer_id}</div>
                        </td>
                        <td>{item.customer_type}</td>
                        <td>{item.status}</td>
                        <td>${formatCurrency(item.outstanding_debt)}</td>
                        <td>
                          ${formatCurrency(item.sales_total)} ({item.sales_count} ventas)
                        </td>
                        <td>
                          {item.last_sale_at
                            ? new Date(item.last_sale_at).toLocaleDateString("es-MX")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="muted-text">
              Configura los filtros y presiona «Actualizar vista» para consultar el portafolio.
            </p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <h3>Dashboard de clientes</h3>
              <p className="muted-text">
                Visualiza las altas mensuales, el top de compradores y el porcentaje de morosos.
              </p>
            </div>
            <div className="report-actions">
              <label>
                Meses
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={dashboardFilters.months}
                  onChange={(event) =>
                    setDashboardFilters((current) => ({
                      ...current,
                      months: Math.max(1, Number(event.target.value)),
                    }))
                  }
                />
              </label>
              <label>
                Top
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={dashboardFilters.topLimit}
                  onChange={(event) =>
                    setDashboardFilters((current) => ({
                      ...current,
                      topLimit: Math.max(1, Number(event.target.value)),
                    }))
                  }
                />
              </label>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => void refreshDashboard()}
                disabled={dashboardLoading}
              >
                {dashboardLoading ? "Actualizando..." : "Actualizar"}
              </button>
            </div>
          </div>

          {dashboardLoading ? (
            <p className="muted-text">Cargando métricas...</p>
          ) : dashboardError ? (
            <p className="error-text">{dashboardError}</p>
          ) : dashboardMetrics ? (
            <div className="dashboard-grid">
              <div className="dashboard-card">
                <h4>Clientes nuevos por mes</h4>
                {dashboardMetrics.new_customers_per_month.length === 0 ? (
                  <p className="muted-text">Sin registros en el rango indicado.</p>
                ) : (
                  <ul className="bars-list">
                    {dashboardMetrics.new_customers_per_month.map((point) => {
                      const normalizedWidth =
                        newCustomersMaxValue > 0
                          ? point.value > 0
                            ? Math.max(
                                8,
                                Math.min(
                                  100,
                                  Math.round(
                                    (point.value / newCustomersMaxValue) * 100,
                                  ),
                                ),
                              )
                            : 0
                          : 0;
                      return (
                        <li key={point.label}>
                          <span>{point.label}</span>
                          <div className="bar">
                            <div
                              className="bar__fill"
                              style={{ width: `${normalizedWidth}%` }}
                            />
                            <span className="bar__value">{point.value}</span>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              <div className="dashboard-card">
                <h4>Top compradores</h4>
                {dashboardMetrics.top_customers.length === 0 ? (
                  <p className="muted-text">No hay ventas registradas.</p>
                ) : (
                  <ul className="summary-list">
                    {dashboardMetrics.top_customers.map((customer) => (
                      <li key={customer.customer_id}>
                        <div>
                          <strong>{customer.name}</strong>
                          <span className="muted-text">
                            {customer.sales_count} ventas · ${
                              formatCurrency(customer.sales_total)
                            }
                          </span>
                        </div>
                        <span className="summary-amount">
                          Deuda ${formatCurrency(customer.outstanding_debt)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="dashboard-card">
                <h4>Morosidad</h4>
                <div className="morosity-indicator">
                  <div className="morosity-ring">
                    <div
                      className="morosity-ring__fill"
                      style={{
                        background: `conic-gradient(#38bdf8 0% ${delinquentRatio.percentage}%, rgba(56, 189, 248, 0.2) ${delinquentRatio.percentage}% 100%)`,
                      }}
                    />
                    <span>{delinquentRatio.percentage}%</span>
                  </div>
                  <div>
                    <p className="muted-text">Clientes morosos identificados</p>
                    <strong>${formatCurrency(delinquentRatio.total)}</strong>
                    <p className="muted-text">Saldo vencido total</p>
                  </div>
                </div>
                <p className="muted-text small">
                  Datos generados el {" "}
                  {new Date(dashboardMetrics.generated_at).toLocaleString("es-MX")}.
                </p>
              </div>
            </div>
          ) : (
            <p className="muted-text">Configura los filtros y presiona actualizar para ver las métricas.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export default Customers;
