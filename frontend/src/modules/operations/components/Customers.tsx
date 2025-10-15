import { useCallback, useEffect, useMemo, useState } from "react";
import type { Customer } from "../../../api";
import {
  createCustomer,
  deleteCustomer,
  exportCustomersCsv,
  listCustomers,
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
  notes: "",
  outstandingDebt: 0,
  historyNote: "",
};

function Customers({ token }: Props) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [form, setForm] = useState<CustomerForm>({ ...initialForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshCustomers = useCallback(
    async (query?: string) => {
      try {
        setLoading(true);
        const data = await listCustomers(
          token,
          query && query.length > 0 ? query : undefined,
          200
        );
        setCustomers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar clientes.");
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

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

  const totalDebt = useMemo(
    () => customers.reduce((acc, customer) => acc + (customer.outstanding_debt ?? 0), 0),
    [customers]
  );

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
      phone: form.phone.trim() || undefined,
      address: form.address.trim() || undefined,
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
      phone: customer.phone ?? "",
      address: customer.address ?? "",
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
      const history = [
        ...customer.history,
        { timestamp: new Date().toISOString(), note: note.trim() },
      ];
      await updateCustomer(token, customer.id, { history }, reason);
      setMessage("Nota añadida correctamente.");
      const trimmed = search.trim();
      await refreshCustomers(trimmed.length >= 2 ? trimmed : undefined);
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

  const handleExport = async () => {
    try {
      setExporting(true);
      const trimmed = search.trim();
      const blob = await exportCustomersCsv(token, trimmed.length >= 2 ? trimmed : undefined);
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
          <input value={form.phone} onChange={(event) => updateForm({ phone: event.target.value })} />
        </label>
        <label className="wide">
          Dirección
          <input value={form.address} onChange={(event) => updateForm({ address: event.target.value })} />
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
                <th>Contacto</th>
                <th>Correo</th>
                <th>Teléfono</th>
                <th>Deuda</th>
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
                return (
                  <tr key={customer.id}>
                    <td>#{customer.id}</td>
                    <td>{customer.name}</td>
                    <td>{customer.contact_name ?? "—"}</td>
                    <td>{customer.email ?? "—"}</td>
                    <td>{customer.phone ?? "—"}</td>
                    <td>${outstanding.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
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
                        <button type="button" className="btn btn--link" onClick={() => handleAdjustDebt(customer)}>
                          Ajustar deuda
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
    </section>
  );
}

export default Customers;
