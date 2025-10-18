import { useCallback, useEffect, useMemo, useState } from "react";
import type {
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
  getCustomerSummary,
  getCustomerPortfolio,
  listCustomers,
  registerCustomerPayment,
  updateCustomer,
} from "../../../api";

type Props = {
  token: string;
};

type CustomerForm = {
  name: string;
  contactName: string;
  email: string;
  phone: string;
  address: string;
  customerType: string;
  status: string;
  creditLimit: number;
  notes: string;
  outstandingDebt: number;
  historyNote: string;
};

const initialForm: CustomerForm = {
  name: "",
  contactName: "",
  email: "",
  phone: "",
  address: "",
  customerType: "minorista",
  status: "activo",
  creditLimit: 0,
  notes: "",
  outstandingDebt: 0,
  historyNote: "",
};

const CUSTOMER_TYPES = [
  { value: "minorista", label: "Minorista" },
  { value: "mayorista", label: "Mayorista" },
  { value: "corporativo", label: "Corporativo" },
];

const CUSTOMER_STATUSES = [
  { value: "activo", label: "Activo" },
  { value: "inactivo", label: "Inactivo" },
  { value: "moroso", label: "Moroso" },
  { value: "vip", label: "VIP" },
  { value: "bloqueado", label: "Bloqueado" },
];

const LEDGER_LABELS: Record<CustomerLedgerEntry["entry_type"], string> = {
  sale: "Cargo por venta",
  payment: "Pago recibido",
  adjustment: "Ajuste",
  note: "Nota registrada",
};

const DEBT_FILTERS = [
  { value: "todos", label: "Todos" },
  { value: "con_deuda", label: "Con saldo pendiente" },
  { value: "sin_deuda", label: "Sin saldo" },
];

function Customers({ token }: Props) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [form, setForm] = useState<CustomerForm>({ ...initialForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CustomerSummary | null>(null);
  const [summaryCustomerId, setSummaryCustomerId] = useState<number | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("todos");
  const [typeFilter, setTypeFilter] = useState<string>("todos");
  const [debtFilter, setDebtFilter] = useState<string>("todos");
  const [portfolioCategory, setPortfolioCategory] = useState<"delinquent" | "frequent">(
    "delinquent"
  );
  const [portfolioLimit, setPortfolioLimit] = useState<number>(10);
  const [portfolioDateFrom, setPortfolioDateFrom] = useState<string>("");
  const [portfolioDateTo, setPortfolioDateTo] = useState<string>("");
  const [portfolioReport, setPortfolioReport] = useState<CustomerPortfolioReport | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [exportingPortfolio, setExportingPortfolio] = useState<"pdf" | "xlsx" | null>(null);
  const [dashboardMetrics, setDashboardMetrics] = useState<CustomerDashboardMetrics | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [dashboardMonths, setDashboardMonths] = useState<number>(6);
  const [dashboardTopLimit, setDashboardTopLimit] = useState<number>(5);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");

  const refreshCustomerSummary = useCallback(
    async (customerId: number) => {
      try {
        setSummaryLoading(true);
        setSummaryError(null);
        const overview = await getCustomerSummary(token, customerId);
        setSummary(overview);
        setSummaryCustomerId(customerId);
      } catch (err) {
        setSummaryError(
          err instanceof Error ? err.message : "No fue posible cargar el resumen del cliente."
        );
      } finally {
        setSummaryLoading(false);
      }
    },
    [token]
  );

  const refreshCustomers = useCallback(
    async (query?: string) => {
      try {
        setLoading(true);
        const data = await listCustomers(token, {
          query: query && query.length > 0 ? query : undefined,
          limit: 200,
          status: statusFilter !== "todos" ? statusFilter : undefined,
          customerType: typeFilter !== "todos" ? typeFilter : undefined,
          hasDebt:
            debtFilter === "con_deuda"
              ? true
              : debtFilter === "sin_deuda"
              ? false
              : undefined,
        });
        const data = await listCustomers(
          token,
          query && query.length > 0 ? query : undefined,
          200,
          {
            status: statusFilter || undefined,
            customerType: typeFilter || undefined,
          }
        );
        setCustomers(data);
        if (summaryCustomerId) {
          const exists = data.some((customer) => customer.id === summaryCustomerId);
          if (exists) {
            void refreshCustomerSummary(summaryCustomerId);
          } else {
            setSummary(null);
            setSummaryCustomerId(null);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar clientes.");
      } finally {
        setLoading(false);
      }
    },
    [
      token,
      summaryCustomerId,
      refreshCustomerSummary,
      statusFilter,
      typeFilter,
      debtFilter,
    ]
  );

  const buildPortfolioParams = useCallback(
    () => ({
      category: portfolioCategory,
      limit: portfolioLimit,
      dateFrom: portfolioDateFrom || undefined,
      dateTo: portfolioDateTo || undefined,
    }),
    [portfolioCategory, portfolioLimit, portfolioDateFrom, portfolioDateTo]
    ]
  );

  const refreshPortfolio = useCallback(async () => {
    try {
      setPortfolioLoading(true);
      setPortfolioError(null);
      const params = buildPortfolioParams();
      const report = await getCustomerPortfolio(token, params);
      setPortfolioReport(report);
    } catch (err) {
      setPortfolioError(
        err instanceof Error ? err.message : "No fue posible obtener el portafolio."
      );
    } finally {
      setPortfolioLoading(false);
    }
  }, [token, buildPortfolioParams]);

  const refreshDashboard = useCallback(async () => {
    try {
      setDashboardLoading(true);
      setDashboardError(null);
      const metrics = await getCustomerDashboardMetrics(token, {
        months: dashboardMonths,
        topLimit: dashboardTopLimit,
      });
      setDashboardMetrics(metrics);
    } catch (err) {
      setDashboardError(
        err instanceof Error ? err.message : "No fue posible cargar el dashboard."
      );
    } finally {
      setDashboardLoading(false);
    }
  }, [token, dashboardMonths, dashboardTopLimit]);

  useEffect(() => {
    void refreshCustomers();
  }, [refreshCustomers]);

  useEffect(() => {
    const trimmed = search.trim();
    const handler = window.setTimeout(() => {
      void refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    }, 350);
    return () => window.clearTimeout(handler);
  }, [search, refreshCustomers]);

  useEffect(() => {
    void refreshPortfolio();
  }, [refreshPortfolio]);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const totalDebt = useMemo(
    () => customers.reduce((acc, customer) => acc + (customer.outstanding_debt ?? 0), 0),
    [customers]
  );

  const formatCurrency = (value: number) =>
    value.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const resolveDetailsValue = useCallback(
    (entry: CustomerLedgerEntry, key: string): string | undefined => {
      const value = entry.details?.[key];
      if (typeof value === "string") {
        return value;
      }
      if (typeof value === "number") {
        return value.toString();
      }
      return undefined;
    },
    []
  );

  const invoiceNumbers = useMemo(() => {
    if (!summary) {
      return new Map<number, string>();
    }
    return new Map(summary.invoices.map((invoice) => [invoice.sale_id, invoice.invoice_number]));
  }, [summary]);

  const maxMonthlyNew = useMemo(() => {
    if (!dashboardMetrics || dashboardMetrics.new_customers_per_month.length === 0) {
      return 1;
    }
    const values = dashboardMetrics.new_customers_per_month.map((point) => point.value);
    const maxValue = Math.max(...values);
    return maxValue <= 0 ? 1 : maxValue;
  }, [dashboardMetrics]);

  const updateForm = (updates: Partial<CustomerForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const resetForm = () => {
    setForm({ ...initialForm });
    setEditingId(null);
  };

  const askReason = (promptText: string): string | null => {
    const reason = window.prompt(promptText, "");
    if (!reason || reason.trim().length < 5) {
      setError("Debes indicar un motivo corporativo válido (mínimo 5 caracteres).");
      return null;
    }
    return reason.trim();
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setError("El nombre del cliente es obligatorio.");
      return;
    }
    const reason = askReason(
      editingId ? "Motivo corporativo para actualizar al cliente" : "Motivo corporativo para registrar al cliente"
    );
    if (!reason) {
      return;
    }
    const payload = {
      name: form.name.trim(),
      contact_name: form.contactName.trim() || undefined,
      email: form.email.trim() || undefined,
      phone: form.phone.trim(),
      address: form.address.trim() || undefined,
      customer_type: form.customerType,
      status: form.status,
      credit_limit: Number.isFinite(form.creditLimit)
        ? Math.max(0, Number(form.creditLimit))
        : 0,
      notes: form.notes.trim() || undefined,
      outstanding_debt: Number.isFinite(form.outstandingDebt)
        ? Math.max(0, Number(form.outstandingDebt))
        : undefined,
    } as Record<string, unknown>;

    try {
      setError(null);
      if (editingId) {
        const existing = customers.find((customer) => customer.id === editingId);
        if (form.historyNote.trim() && existing) {
          payload.history = [
            ...existing.history,
            { timestamp: new Date().toISOString(), note: form.historyNote.trim() },
          ];
        }
        await updateCustomer(token, editingId, payload, reason);
        setMessage("Cliente actualizado correctamente.");
      } else {
        if (form.historyNote.trim()) {
          payload.history = [
            { timestamp: new Date().toISOString(), note: form.historyNote.trim() },
          ];
        }
        await createCustomer(token, payload, reason);
        setMessage("Cliente registrado exitosamente.");
      }
      resetForm();
      const trimmed = search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar la información del cliente.");
    }
  };

  const handleEdit = (customer: Customer) => {
    setEditingId(customer.id);
    setForm({
      name: customer.name,
      contactName: customer.contact_name ?? "",
      email: customer.email ?? "",
      phone: customer.phone,
      address: customer.address ?? "",
      customerType: customer.customer_type ?? "minorista",
      status: customer.status ?? "activo",
      creditLimit: Number(customer.credit_limit ?? 0),
      notes: customer.notes ?? "",
      outstandingDebt: Number(customer.outstanding_debt ?? 0),
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
      await deleteCustomer(token, customer.id, reason);
      setMessage("Cliente eliminado.");
      const trimmed = search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (editingId === customer.id) {
        resetForm();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible eliminar al cliente.");
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
      setMessage("Nota añadida correctamente.");
      const trimmed = search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (summaryCustomerId === customer.id) {
        void refreshCustomerSummary(customer.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible agregar la nota.");
    }
  };

  const handleAdjustDebt = async (customer: Customer) => {
    const amountRaw = window.prompt(
      "Nuevo saldo pendiente",
      String(Number(customer.outstanding_debt ?? 0).toFixed(2))
    );
    if (amountRaw === null) {
      return;
    }
    const amount = Number(amountRaw);
    if (!Number.isFinite(amount) || amount < 0) {
      setError("Indica un monto válido para la deuda.");
      return;
    }
    const reason = askReason("Motivo corporativo para ajustar la deuda");
    if (!reason) {
      return;
    }
    try {
      await updateCustomer(token, customer.id, { outstanding_debt: amount }, reason);
      setMessage("Saldo actualizado correctamente.");
      const trimmed = search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible ajustar la deuda.");
    }
  };

  const handleRegisterPayment = async (customer: Customer) => {
    const amountRaw = window.prompt("Monto del pago", "0.00");
    if (amountRaw === null) {
      return;
    }
    const amount = Number(amountRaw);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Indica un monto válido y mayor a cero para el pago.");
      return;
    }
    const methodInput = window.prompt("Método de pago", "transferencia") ?? "";
    const referenceInput = window.prompt("Referencia del pago (opcional)", "");
    const noteInput = window.prompt("Nota interna del pago (opcional)", "");
    const saleReference = window.prompt("ID de venta asociada (opcional)", "");
    const reason = askReason("Motivo corporativo para registrar el pago");
    if (!reason) {
      return;
    }
    const payload = {
      amount: Number(amount.toFixed(2)),
      method: methodInput.trim() || "manual",
      reference: referenceInput && referenceInput.trim() ? referenceInput.trim() : undefined,
      note: noteInput && noteInput.trim() ? noteInput.trim() : undefined,
      sale_id:
        saleReference && saleReference.trim().length > 0
          ? Number(saleReference.trim())
          : undefined,
    } as const;
    if (payload.sale_id !== undefined && !Number.isFinite(payload.sale_id)) {
      setError("Indica un ID de venta válido o deja el campo vacío.");
      return;
    }
    try {
      await registerCustomerPayment(token, customer.id, payload, reason);
      setMessage("Pago registrado correctamente.");
      const trimmed = search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
      if (summaryCustomerId === customer.id) {
        void refreshCustomerSummary(customer.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible registrar el pago.");
    }
  };

  const handleViewSummary = (customer: Customer) => {
    setSummaryError(null);
    void refreshCustomerSummary(customer.id);
  };

  const handleCloseSummary = () => {
    setSummary(null);
    setSummaryCustomerId(null);
    setSummaryError(null);
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const trimmed = search.trim();
      const blob = await exportCustomersCsv(
        token,
        trimmed.length >= 2 ? trimmed : undefined,
        {
          status: statusFilter || undefined,
          customerType: typeFilter || undefined,
        }
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "clientes_softmobile.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setMessage("Exportación CSV generada correctamente.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar el CSV de clientes.");
    } finally {
      setExporting(false);
    }
  };

  const handleExportPortfolio = async (format: "pdf" | "xlsx") => {
    const reason = askReason(
      format === "pdf"
        ? "Motivo corporativo para exportar el reporte PDF"
        : "Motivo corporativo para exportar el reporte Excel"
    );
    if (!reason) {
      return;
    }
    try {
      setPortfolioError(null);
      setExportingPortfolio(format);
      const params = buildPortfolioParams();
      const blob =
        format === "pdf"
          ? await exportCustomerPortfolioPdf(token, params, reason)
          : await exportCustomerPortfolioExcel(token, params, reason);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download =
        format === "pdf"
          ? `clientes_${params.category}.pdf`
          : `clientes_${params.category}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setMessage(
        format === "pdf"
          ? "Reporte PDF de clientes generado correctamente."
          : "Reporte Excel de clientes generado correctamente."
      );
    } catch (err) {
      setPortfolioError(
        err instanceof Error
          ? err.message
          : "No fue posible exportar el reporte de clientes."
      );
    } finally {
      setExportingPortfolio(null);
    }
  };

  return (
    <section className="card wide">
      <h2>Clientes corporativos</h2>
      <p className="card-subtitle">
        Administra perfiles de clientes, notas de contacto y saldos pendientes para el POS y reportes.
      </p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          Nombre del cliente
          <input value={form.name} onChange={(event) => updateForm({ name: event.target.value })} required />
        </label>
        <label>
          Contacto principal
          <input value={form.contactName} onChange={(event) => updateForm({ contactName: event.target.value })} />
        </label>
        <label>
          Correo electrónico
          <input
            type="email"
            value={form.email}
            onChange={(event) => updateForm({ email: event.target.value })}
            placeholder="cliente@empresa.com"
          />
        </label>
        <label>
          Teléfono
          <input
            value={form.phone}
            onChange={(event) => updateForm({ phone: event.target.value })}
            required
          />
        </label>
        <label>
          Tipo de cliente
          <select value={form.customerType} onChange={(event) => updateForm({ customerType: event.target.value })}>
            {CUSTOMER_TYPES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Estado
          <select value={form.status} onChange={(event) => updateForm({ status: event.target.value })}>
            {CUSTOMER_STATUSES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="wide">
          Dirección
          <input value={form.address} onChange={(event) => updateForm({ address: event.target.value })} />
        </label>
        <label>
          Límite de crédito
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.creditLimit}
            onChange={(event) => updateForm({ creditLimit: Number(event.target.value) })}
          />
        </label>
        <label>
          Saldo pendiente
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.outstandingDebt}
            onChange={(event) => updateForm({ outstandingDebt: Number(event.target.value) })}
          />
        </label>
        <label className="wide">
          Notas internas
          <textarea
            value={form.notes}
            onChange={(event) => updateForm({ notes: event.target.value })}
            rows={2}
            placeholder="Observaciones generales del cliente"
          />
        </label>
        <label className="wide">
          Nota inicial para historial (opcional)
          <textarea
            value={form.historyNote}
            onChange={(event) => updateForm({ historyNote: event.target.value })}
            rows={2}
            placeholder="Ej. Cliente recurrente de servicio premium"
          />
        </label>
        <div className="actions-row wide">
          <button type="submit" className="btn btn--primary">
            {editingId ? "Actualizar cliente" : "Agregar cliente"}
          </button>
          {editingId ? (
            <button type="button" className="btn btn--ghost" onClick={resetForm}>
              Cancelar edición
            </button>
          ) : null}
          <button type="button" className="btn btn--secondary" onClick={handleExport} disabled={exporting}>
            {exporting ? "Exportando..." : "Exportar CSV"}
          </button>
        </div>
      </form>
      <div className="form-grid">
        <label className="wide">
          Buscar clientes
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Nombre, correo, nota o contacto"
          />
          <span className="muted-text">Se refresca automáticamente al escribir.</span>
        </label>
        <label>
          Estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="todos">Todos</option>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">Todos</option>
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
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
          >
            <option value="todos">Todos</option>
          <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="">Todos</option>
            {CUSTOMER_TYPES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Saldo pendiente
          <select value={debtFilter} onChange={(event) => setDebtFilter(event.target.value)}>
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
          <strong>${totalDebt.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
        </div>
      </div>
      {loading ? (
        <p className="muted-text">Cargando información de clientes...</p>
      ) : customers.length === 0 ? (
        <p className="muted-text">Aún no se registran clientes con los filtros actuales.</p>
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
                <th>Última nota</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => {
                const historyLength = customer.history.length;
                const lastHistory = historyLength
                  ? customer.history[historyLength - 1].note
                  : "—";
                const lastInteraction = customer.last_interaction_at
                  ? new Date(customer.last_interaction_at).toLocaleString("es-MX")
                  : "—";
                const outstanding = Number(customer.outstanding_debt ?? 0);
                const creditLimit = Number(customer.credit_limit ?? 0);
                return (
                  <tr key={customer.id}>
                    <td>#{customer.id}</td>
                    <td>{customer.name}</td>
                    <td className="muted-text">{customer.customer_type ?? "—"}</td>
                    <td>{customer.status ?? "—"}</td>
                    <td>{customer.contact_name ?? "—"}</td>
                    <td>{customer.email ?? "—"}</td>
                    <td>{customer.phone}</td>
                    <td>
                      ${creditLimit.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td>
                      ${outstanding.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td>{lastInteraction}</td>
                    <td>{lastHistory}</td>
                    <td>
                      <div className="actions-row">
                        <button type="button" className="btn btn--link" onClick={() => handleEdit(customer)}>
                          Editar
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleAddNote(customer)}>
                          Nota
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleRegisterPayment(customer)}>
                          Pago
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleAdjustDebt(customer)}>
                          Ajustar deuda
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleViewSummary(customer)}>
                          Resumen
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleDelete(customer)}>
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
      {summaryCustomerId ? (
        <section className="card">
          <div className="actions-row">
            <h3>Resumen financiero y de control</h3>
            <button type="button" className="btn btn--ghost" onClick={handleCloseSummary}>
              Cerrar resumen
            </button>
          </div>
          {summaryError ? <div className="alert error">{summaryError}</div> : null}
          {summaryLoading ? (
            <p className="muted-text">Consultando resumen del cliente seleccionado...</p>
          ) : summary ? (
            <>
              <div className="form-grid">
                <div>
                  <span className="muted-text">Cliente</span>
                  <strong>{summary.customer.name}</strong>
                  <span className="muted-text">
                    Estado: {summary.customer.status} · Tipo: {summary.customer.customer_type}
                  </span>
                </div>
                <div>
                  <span className="muted-text">Crédito autorizado</span>
                  <strong>${formatCurrency(summary.totals.credit_limit)}</strong>
                </div>
                <div>
                  <span className="muted-text">Saldo actual</span>
                  <strong>${formatCurrency(summary.totals.outstanding_debt)}</strong>
                </div>
                <div>
                  <span className="muted-text">Crédito disponible</span>
                  <strong>${formatCurrency(summary.totals.available_credit)}</strong>
                </div>
                <div>
                  <span className="muted-text">Cargos a crédito</span>
                  <strong>${formatCurrency(summary.totals.total_sales_credit)}</strong>
                </div>
                <div>
                  <span className="muted-text">Pagos aplicados</span>
                  <strong>${formatCurrency(summary.totals.total_payments)}</strong>
                </div>
              </div>
              <h4>Ventas recientes</h4>
              {summary.sales.length === 0 ? (
                <p className="muted-text">Sin ventas registradas para este cliente.</p>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Venta</th>
                        <th>Factura</th>
                        <th>Total</th>
                        <th>Estado</th>
                        <th>Fecha</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.sales.slice(0, 5).map((sale) => (
                        <tr key={sale.sale_id}>
                          <td>#{sale.sale_id}</td>
                          <td>{invoiceNumbers.get(sale.sale_id) ?? "—"}</td>
                          <td>${formatCurrency(sale.total_amount)}</td>
                          <td>{sale.status}</td>
                          <td>{new Date(sale.created_at).toLocaleString("es-MX")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <h4>Pagos registrados</h4>
              {summary.payments.length === 0 ? (
                <p className="muted-text">Sin pagos asociados en la bitácora reciente.</p>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Monto</th>
                        <th>Método</th>
                        <th>Referencia</th>
                        <th>Nota</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.payments.slice(0, 5).map((entry) => {
                        const methodValue = resolveDetailsValue(entry, "method") ?? "manual";
                        const referenceValue = resolveDetailsValue(entry, "reference");
                        return (
                          <tr key={entry.id}>
                            <td>{new Date(entry.created_at).toLocaleString("es-MX")}</td>
                            <td>${formatCurrency(Math.abs(entry.amount))}</td>
                            <td>{methodValue.toUpperCase()}</td>
                            <td>{referenceValue ?? "—"}</td>
                            <td>{entry.note ?? "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              <h4>Bitácora reciente</h4>
              {summary.ledger.length === 0 ? (
                <p className="muted-text">No hay movimientos registrados para este cliente.</p>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Tipo</th>
                        <th>Monto</th>
                        <th>Saldo después</th>
                        <th>Detalle</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.ledger.slice(0, 6).map((entry) => {
                        const detailText = entry.note ?? resolveDetailsValue(entry, "event") ?? "—";
                        return (
                          <tr key={entry.id}>
                            <td>{new Date(entry.created_at).toLocaleString("es-MX")}</td>
                            <td>{LEDGER_LABELS[entry.entry_type]}</td>
                            <td>${formatCurrency(entry.amount)}</td>
                            <td>${formatCurrency(entry.balance_after)}</td>
                            <td>{detailText}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : null}
        </section>
      ) : null}
      <section className="card">
        <div className="actions-row">
          <h3>Reportes de clientes corporativos</h3>
          <div className="actions-row">
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => handleExportPortfolio("pdf")}
              disabled={exportingPortfolio === "pdf" || portfolioLoading}
            >
              {exportingPortfolio === "pdf" ? "Exportando PDF..." : "Exportar PDF"}
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => handleExportPortfolio("xlsx")}
              disabled={exportingPortfolio === "xlsx" || portfolioLoading}
            >
              {exportingPortfolio === "xlsx" ? "Exportando Excel..." : "Exportar Excel"}
            </button>
          </div>
        </div>
        <p className="card-subtitle">
          Descarga reportes temáticos en PDF o Excel de clientes morosos o compradores frecuentes.
        </p>
        {portfolioError ? <div className="alert error">{portfolioError}</div> : null}
        <div className="form-grid">
          <label>
            Categoría
            <select
              value={portfolioCategory}
              onChange={(event) =>
                setPortfolioCategory(event.target.value as "delinquent" | "frequent")
              }
            >
              <option value="delinquent">Clientes morosos</option>
              <option value="frequent">Compradores frecuentes</option>
            </select>
          </label>
          <label>
            Límite de filas
            <input
              type="number"
              min={1}
              max={500}
              value={portfolioLimit}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (Number.isNaN(value)) {
                  setPortfolioLimit(1);
                  return;
                }
                setPortfolioLimit(Math.min(500, Math.max(1, Math.trunc(value))));
              }}
            />
          </label>
          <label>
            Desde
            <input
              type="date"
              value={portfolioDateFrom}
              onChange={(event) => setPortfolioDateFrom(event.target.value)}
            />
          </label>
          <label>
            Hasta
            <input
              type="date"
              value={portfolioDateTo}
              onChange={(event) => setPortfolioDateTo(event.target.value)}
            />
          </label>
          <div className="actions-row wide">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={refreshPortfolio}
              disabled={portfolioLoading}
            >
              {portfolioLoading ? "Actualizando..." : "Actualizar panel"}
            </button>
          </div>
        </div>
        {portfolioLoading ? (
          <p className="muted-text">Generando resumen de portafolio...</p>
        ) : portfolioReport ? (
          <>
            <div className="form-grid">
              <div>
                <span className="muted-text">Generado</span>
                <strong>
                  {new Date(portfolioReport.generated_at).toLocaleString("es-MX")}
                </strong>
              </div>
              <div>
                <span className="muted-text">Clientes incluidos</span>
                <strong>{portfolioReport.totals.customers}</strong>
              </div>
              <div>
                <span className="muted-text">Marcados morosos</span>
                <strong>{portfolioReport.totals.moroso_flagged}</strong>
              </div>
              <div>
                <span className="muted-text">Deuda consolidada</span>
                <strong>${formatCurrency(portfolioReport.totals.outstanding_debt)}</strong>
              </div>
              <div>
                <span className="muted-text">Ventas acumuladas</span>
                <strong>${formatCurrency(portfolioReport.totals.sales_total)}</strong>
              </div>
            </div>
            {portfolioReport.items.length === 0 ? (
              <p className="muted-text">No hay clientes que coincidan con los filtros actuales.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Estado</th>
                      <th>Tipo</th>
                      <th>Crédito</th>
                      <th>Saldo</th>
                      <th>Disponible</th>
                      <th>Ventas</th>
                      <th>Operaciones</th>
                      <th>Última venta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolioReport.items.map((item) => (
                      <tr key={item.customer_id}>
                        <td>{item.name}</td>
                        <td>{item.status}</td>
                        <td>{item.customer_type}</td>
                        <td>${formatCurrency(item.credit_limit)}</td>
                        <td>${formatCurrency(item.outstanding_debt)}</td>
                        <td>${formatCurrency(item.available_credit)}</td>
                        <td>${formatCurrency(item.sales_total)}</td>
                        <td>{item.sales_count}</td>
                        <td>
                          {item.last_sale_at
                            ? new Date(item.last_sale_at).toLocaleString("es-MX")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <p className="muted-text">
            Configura los filtros y pulsa «Actualizar panel» para generar el portafolio.
          </p>
        )}
      </section>
      <section className="card">
        <div className="actions-row">
          <h3>Dashboard de comportamiento de clientes</h3>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={refreshDashboard}
            disabled={dashboardLoading}
          >
            {dashboardLoading ? "Actualizando..." : "Actualizar métricas"}
          </button>
        </div>
        <p className="card-subtitle">
          Visualiza altas mensuales, saldos y el top de compradores con el tema oscuro corporativo.
        </p>
        {dashboardError ? <div className="alert error">{dashboardError}</div> : null}
        <div className="form-grid">
          <label>
            Meses a evaluar
            <input
              type="number"
              min={1}
              max={24}
              value={dashboardMonths}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (Number.isNaN(value)) {
                  setDashboardMonths(1);
                  return;
                }
                setDashboardMonths(Math.min(24, Math.max(1, Math.trunc(value))));
              }}
            />
          </label>
          <label>
            Top compradores
            <input
              type="number"
              min={1}
              max={50}
              value={dashboardTopLimit}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (Number.isNaN(value)) {
                  setDashboardTopLimit(1);
                  return;
                }
                setDashboardTopLimit(Math.min(50, Math.max(1, Math.trunc(value))));
              }}
            />
          </label>
        </div>
        {dashboardLoading ? (
          <p className="muted-text">Consultando métricas de clientes...</p>
        ) : dashboardMetrics ? (
          <>
            <div className="form-grid">
              <div>
                <span className="muted-text">Clientes con deuda</span>
                <strong>{dashboardMetrics.delinquent_summary.customers_with_debt}</strong>
              </div>
              <div>
                <span className="muted-text">Marcados como morosos</span>
                <strong>{dashboardMetrics.delinquent_summary.moroso_flagged}</strong>
              </div>
              <div>
                <span className="muted-text">Deuda total</span>
                <strong>
                  ${formatCurrency(dashboardMetrics.delinquent_summary.total_outstanding_debt)}
                </strong>
              </div>
            </div>
            <h4>Nuevos clientes por mes</h4>
            {dashboardMetrics.new_customers_per_month.length === 0 ? (
              <p className="muted-text">Sin registros de nuevos clientes en el periodo.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Mes</th>
                      <th>Actividad</th>
                      <th>Nuevos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardMetrics.new_customers_per_month.map((point) => {
                      const percentage = Math.round((point.value / maxMonthlyNew) * 100);
                      return (
                        <tr key={point.label}>
                          <td>{point.label}</td>
                          <td>
                            <div
                              style={{
                                background: "#1f2937",
                                borderRadius: "6px",
                                height: "8px",
                                width: "100%",
                              }}
                            >
                              <div
                                style={{
                                  width: `${percentage}%`,
                                  background: "#38bdf8",
                                  height: "8px",
                                  borderRadius: "6px",
                                }}
                              />
                            </div>
                          </td>
                          <td>{point.value}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <h4>Top compradores</h4>
            {dashboardMetrics.top_customers.length === 0 ? (
              <p className="muted-text">Aún no hay clientes destacados en ventas.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Estado</th>
                      <th>Ventas</th>
                      <th>Operaciones</th>
                      <th>Saldo</th>
                      <th>Última compra</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardMetrics.top_customers.map((item) => (
                      <tr key={item.customer_id}>
                        <td>{item.name}</td>
                        <td>{item.status}</td>
                        <td>${formatCurrency(item.sales_total)}</td>
                        <td>{item.sales_count}</td>
                        <td>${formatCurrency(item.outstanding_debt)}</td>
                        <td>
                          {item.last_sale_at
                            ? new Date(item.last_sale_at).toLocaleString("es-MX")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <p className="muted-text">
            Ajusta los parámetros y pulsa «Actualizar métricas» para consultar el dashboard de clientes.
          </p>
        )}
      </section>
    </section>
  );
}

export default Customers;
