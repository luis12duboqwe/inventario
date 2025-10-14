import { useCallback, useEffect, useMemo, useState } from "react";
import type { Supplier } from "../api";
import {
  createSupplier,
  deleteSupplier,
  exportSuppliersCsv,
  listSuppliers,
  updateSupplier,
} from "../api";

type Props = {
  token: string;
};

type SupplierForm = {
  name: string;
  contactName: string;
  email: string;
  phone: string;
  address: string;
  notes: string;
  outstandingDebt: number;
  historyNote: string;
};

const initialForm: SupplierForm = {
  name: "",
  contactName: "",
  email: "",
  phone: "",
  address: "",
  notes: "",
  outstandingDebt: 0,
  historyNote: "",
};

function Suppliers({ token }: Props) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [form, setForm] = useState<SupplierForm>({ ...initialForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshSuppliers = useCallback(
    async (query?: string) => {
      try {
        setLoading(true);
        const data = await listSuppliers(
          token,
          query && query.length > 0 ? query : undefined,
          200
        );
        setSuppliers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No fue posible cargar proveedores.");
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  useEffect(() => {
    void refreshSuppliers();
  }, [refreshSuppliers]);

  useEffect(() => {
    const trimmed = search.trim();
    const handler = window.setTimeout(() => {
      void refreshSuppliers(trimmed.length >= 2 ? trimmed : undefined);
    }, 350);
    return () => window.clearTimeout(handler);
  }, [search, refreshSuppliers]);

  const totalDebt = useMemo(
    () => suppliers.reduce((acc, supplier) => acc + (supplier.outstanding_debt ?? 0), 0),
    [suppliers]
  );

  const updateForm = (updates: Partial<SupplierForm>) => {
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
      setError("El nombre del proveedor es obligatorio.");
      return;
    }
    const reason = askReason(
      editingId ? "Motivo corporativo para actualizar al proveedor" : "Motivo corporativo para registrar al proveedor"
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
        const existing = suppliers.find((supplier) => supplier.id === editingId);
        if (form.historyNote.trim() && existing) {
          payload.history = [
            ...existing.history,
            { timestamp: new Date().toISOString(), note: form.historyNote.trim() },
          ];
        }
        await updateSupplier(token, editingId, payload, reason);
        setMessage("Proveedor actualizado correctamente.");
      } else {
        if (form.historyNote.trim()) {
          payload.history = [
            { timestamp: new Date().toISOString(), note: form.historyNote.trim() },
          ];
        }
        await createSupplier(token, payload, reason);
        setMessage("Proveedor registrado exitosamente.");
      }
      resetForm();
      const trimmed = search.trim();
      await refreshSuppliers(trimmed.length >= 2 ? trimmed : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar la información del proveedor.");
    }
  };

  const handleEdit = (supplier: Supplier) => {
    setEditingId(supplier.id);
    setForm({
      name: supplier.name,
      contactName: supplier.contact_name ?? "",
      email: supplier.email ?? "",
      phone: supplier.phone ?? "",
      address: supplier.address ?? "",
      notes: supplier.notes ?? "",
      outstandingDebt: Number(supplier.outstanding_debt ?? 0),
      historyNote: "",
    });
  };

  const handleDelete = async (supplier: Supplier) => {
    if (!window.confirm(`¿Eliminar al proveedor ${supplier.name}?`)) {
      return;
    }
    const reason = askReason("Motivo corporativo para eliminar al proveedor");
    if (!reason) {
      return;
    }
    try {
      await deleteSupplier(token, supplier.id, reason);
      setMessage("Proveedor eliminado.");
      const trimmed = search.trim();
      await refreshSuppliers(trimmed.length >= 2 ? trimmed : undefined);
      if (editingId === supplier.id) {
        resetForm();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible eliminar al proveedor.");
    }
  };

  const handleAddNote = async (supplier: Supplier) => {
    const note = window.prompt("Nueva nota para el proveedor", "");
    if (!note || !note.trim()) {
      return;
    }
    const reason = askReason("Motivo corporativo para registrar la nota del proveedor");
    if (!reason) {
      return;
    }
    try {
      const history = [
        ...supplier.history,
        { timestamp: new Date().toISOString(), note: note.trim() },
      ];
      await updateSupplier(token, supplier.id, { history }, reason);
      setMessage("Nota agregada correctamente.");
      const trimmed = search.trim();
      await refreshSuppliers(trimmed.length >= 2 ? trimmed : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible agregar la nota al proveedor.");
    }
  };

  const handleAdjustDebt = async (supplier: Supplier) => {
    const amountRaw = window.prompt(
      "Nuevo saldo pendiente",
      String(Number(supplier.outstanding_debt ?? 0).toFixed(2))
    );
    if (amountRaw === null) {
      return;
    }
    const amount = Number(amountRaw);
    if (!Number.isFinite(amount) || amount < 0) {
      setError("Indica un monto válido para la deuda del proveedor.");
      return;
    }
    const reason = askReason("Motivo corporativo para ajustar la cuenta del proveedor");
    if (!reason) {
      return;
    }
    try {
      await updateSupplier(token, supplier.id, { outstanding_debt: amount }, reason);
      setMessage("Saldo del proveedor actualizado.");
      const trimmed = search.trim();
      await refreshSuppliers(trimmed.length >= 2 ? trimmed : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible ajustar la cuenta del proveedor.");
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const trimmed = search.trim();
      const blob = await exportSuppliersCsv(token, trimmed.length >= 2 ? trimmed : undefined);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "proveedores_softmobile.csv";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setMessage("Exportación CSV de proveedores generada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible exportar el CSV de proveedores.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="card wide">
      <h2>Proveedores estratégicos</h2>
      <p className="card-subtitle">
        Centraliza información de proveedores, notas de servicio y saldos pendientes para compras y reparaciones.
      </p>
      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}
      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          Nombre del proveedor
          <input value={form.name} onChange={(event) => updateForm({ name: event.target.value })} required />
        </label>
        <label>
          Contacto
          <input value={form.contactName} onChange={(event) => updateForm({ contactName: event.target.value })} />
        </label>
        <label>
          Correo
          <input
            type="email"
            value={form.email}
            onChange={(event) => updateForm({ email: event.target.value })}
            placeholder="proveedor@empresa.com"
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
          Notas
          <textarea
            value={form.notes}
            onChange={(event) => updateForm({ notes: event.target.value })}
            rows={2}
            placeholder="Condiciones comerciales, entregas, SLA"
          />
        </label>
        <label className="wide">
          Nota inicial para historial (opcional)
          <textarea
            value={form.historyNote}
            onChange={(event) => updateForm({ historyNote: event.target.value })}
            rows={2}
            placeholder="Ej. Garantía de 90 días en refacciones"
          />
        </label>
        <div className="actions-row wide">
          <button type="submit" className="button primary">
            {editingId ? "Actualizar proveedor" : "Agregar proveedor"}
          </button>
          {editingId ? (
            <button type="button" className="button ghost" onClick={resetForm}>
              Cancelar edición
            </button>
          ) : null}
          <button type="button" className="button secondary" onClick={handleExport} disabled={exporting}>
            {exporting ? "Exportando..." : "Exportar CSV"}
          </button>
        </div>
      </form>
      <div className="form-grid">
        <label className="wide">
          Buscar proveedores
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Nombre, contacto o nota"
          />
          <span className="muted-text">Escribe al menos 2 caracteres para filtrar.</span>
        </label>
        <div>
          <span className="muted-text">Proveedores activos</span>
          <strong>{suppliers.length}</strong>
        </div>
        <div>
          <span className="muted-text">Saldo pendiente</span>
          <strong>${totalDebt.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
        </div>
      </div>
      {loading ? (
        <p className="muted-text">Cargando proveedores...</p>
      ) : suppliers.length === 0 ? (
        <p className="muted-text">Aún no se registran proveedores con los filtros actuales.</p>
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
                <th>Saldo</th>
                <th>Última nota</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => {
                const historyLength = supplier.history.length;
                const lastHistory = historyLength
                  ? supplier.history[historyLength - 1].note
                  : "—";
                const outstanding = Number(supplier.outstanding_debt ?? 0);
                return (
                  <tr key={supplier.id}>
                    <td>#{supplier.id}</td>
                    <td>{supplier.name}</td>
                    <td>{supplier.contact_name ?? "—"}</td>
                    <td>{supplier.email ?? "—"}</td>
                    <td>{supplier.phone ?? "—"}</td>
                    <td>${outstanding.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td>{lastHistory}</td>
                    <td>
                      <div className="actions-row">
                        <button type="button" className="button link" onClick={() => handleEdit(supplier)}>
                          Editar
                        </button>
                        <button type="button" className="button link" onClick={() => handleAddNote(supplier)}>
                          Nota
                        </button>
                        <button type="button" className="button link" onClick={() => handleAdjustDebt(supplier)}>
                          Ajustar saldo
                        </button>
                        <button type="button" className="button link" onClick={() => handleDelete(supplier)}>
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

export default Suppliers;
