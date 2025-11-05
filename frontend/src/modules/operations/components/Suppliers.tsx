import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  ContactHistoryEntry,
  Store,
  Supplier,
  SupplierBatch,
  SupplierBatchPayload,
  SupplierPayload,
} from "../../../api";
import {
  createSupplier,
  createSupplierBatch,
  deleteSupplier,
  deleteSupplierBatch,
  exportSuppliersCsv,
  listSupplierBatches,
  listSuppliers,
  updateSupplier,
  updateSupplierBatch,
} from "../../../api";

type Props = {
  token: string;
  stores: Store[];
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

type SupplierBatchForm = {
  storeId: number | "";
  deviceId: number | "";
  modelName: string;
  batchCode: string;
  unitCost: number;
  quantity: number;
  purchaseDate: string;
  notes: string;
};

const createInitialBatchForm = (): SupplierBatchForm => ({
  storeId: "",
  deviceId: "",
  modelName: "",
  batchCode: "",
  unitCost: 0,
  quantity: 0,
  purchaseDate: new Date().toISOString().slice(0, 10),
  notes: "",
});

function Suppliers({ token, stores }: Props) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [form, setForm] = useState<SupplierForm>({ ...initialForm });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedSupplierId, setSelectedSupplierId] = useState<number | null>(null);
  const [selectedSupplierName, setSelectedSupplierName] = useState<string | null>(null);
  const [batches, setBatches] = useState<SupplierBatch[]>([]);
  const [batchForm, setBatchForm] = useState<SupplierBatchForm>(createInitialBatchForm);
  const [batchEditingId, setBatchEditingId] = useState<number | null>(null);
  const [loadingBatches, setLoadingBatches] = useState(false);
  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }),
    []
  );

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

  const refreshBatches = useCallback(
    async (supplierId: number) => {
      try {
        setLoadingBatches(true);
        const data = await listSupplierBatches(token, supplierId, 100);
        setBatches(data);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "No fue posible cargar los lotes del proveedor."
        );
      } finally {
        setLoadingBatches(false);
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

  const storeLookup = useMemo(() => {
    const map = new Map<number, string>();
    stores.forEach((store) => map.set(store.id, store.name));
    return map;
  }, [stores]);

  const updateForm = (updates: Partial<SupplierForm>) => {
    setForm((current) => ({ ...current, ...updates }));
  };

  const updateBatchForm = (updates: Partial<SupplierBatchForm>) => {
    setBatchForm((current) => ({ ...current, ...updates }));
  };

  const resetForm = () => {
    setForm({ ...initialForm });
    setEditingId(null);
  };

  const resetBatchForm = () => {
    setBatchForm(createInitialBatchForm());
    setBatchEditingId(null);
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
    const trimmedName = form.name.trim();
    const contactName = form.contactName.trim();
    const email = form.email.trim();
    const phone = form.phone.trim();
    const address = form.address.trim();
    const notes = form.notes.trim();
    const outstandingValue = Number.isFinite(form.outstandingDebt)
      ? Math.max(0, Number(form.outstandingDebt))
      : null;

    try {
      setError(null);
      if (editingId) {
        const payload: Partial<SupplierPayload> = { name: trimmedName };
        if (contactName) {
          payload.contact_name = contactName;
        }
        if (email) {
          payload.email = email;
        }
        if (phone) {
          payload.phone = phone;
        }
        if (address) {
          payload.address = address;
        }
        if (notes) {
          payload.notes = notes;
        }
        if (outstandingValue !== null) {
          payload.outstanding_debt = outstandingValue;
        }
        const existing = suppliers.find((supplier) => supplier.id === editingId);
        if (form.historyNote.trim() && existing) {
          const historyEntries: ContactHistoryEntry[] = [
            ...existing.history,
            { timestamp: new Date().toISOString(), note: form.historyNote.trim() },
          ];
          payload.history = historyEntries;
        }
        await updateSupplier(token, editingId, payload, reason);
        setMessage("Proveedor actualizado correctamente.");
      } else {
        const payload: SupplierPayload = { name: trimmedName };
        if (contactName) {
          payload.contact_name = contactName;
        }
        if (email) {
          payload.email = email;
        }
        if (phone) {
          payload.phone = phone;
        }
        if (address) {
          payload.address = address;
        }
        if (notes) {
          payload.notes = notes;
        }
        if (outstandingValue !== null) {
          payload.outstanding_debt = outstandingValue;
        }
        if (form.historyNote.trim()) {
          const historyEntries: ContactHistoryEntry[] = [
            { timestamp: new Date().toISOString(), note: form.historyNote.trim() },
          ];
          payload.history = historyEntries;
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
    setSelectedSupplierId(supplier.id);
    setSelectedSupplierName(supplier.name);
    resetBatchForm();
    void refreshBatches(supplier.id);
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
      if (selectedSupplierId === supplier.id) {
        setSelectedSupplierId(null);
        setSelectedSupplierName(null);
        setBatches([]);
        resetBatchForm();
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

  const handleSelectBatches = (supplier: Supplier) => {
    setSelectedSupplierId(supplier.id);
    setSelectedSupplierName(supplier.name);
    resetBatchForm();
    void refreshBatches(supplier.id);
  };

  const handleBatchEdit = (batch: SupplierBatch) => {
    setBatchEditingId(batch.id);
    setBatchForm({
      storeId: batch.store_id ?? "",
      deviceId: batch.device_id ?? "",
      modelName: batch.model_name,
      batchCode: batch.batch_code,
      unitCost: batch.unit_cost,
      quantity: batch.quantity,
      purchaseDate: batch.purchase_date,
      notes: batch.notes ?? "",
    });
  };

  const handleBatchDelete = async (batch: SupplierBatch) => {
    if (!window.confirm(`¿Eliminar el lote ${batch.batch_code}?`)) {
      return;
    }
    const reason = askReason("Motivo corporativo para eliminar el lote del proveedor");
    if (!reason) {
      return;
    }
    try {
      await deleteSupplierBatch(token, batch.id, reason);
      setMessage("Lote eliminado.");
      if (selectedSupplierId) {
        await refreshBatches(selectedSupplierId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible eliminar el lote del proveedor.");
    }
  };

  const handleBatchSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedSupplierId) {
      setError("Selecciona un proveedor para gestionar sus lotes.");
      return;
    }
    if (!batchForm.modelName.trim() || !batchForm.batchCode.trim()) {
      setError("Indica el modelo y el código de lote.");
      return;
    }
    if (!batchForm.purchaseDate) {
      setError("Selecciona la fecha de compra del lote.");
      return;
    }
    const unitCostValue = Number(batchForm.unitCost);
    if (!Number.isFinite(unitCostValue) || unitCostValue < 0) {
      setError("Indica un costo unitario válido.");
      return;
    }
    const reason = askReason(
      batchEditingId
        ? "Motivo corporativo para actualizar el lote del proveedor"
        : "Motivo corporativo para registrar el lote del proveedor"
    );
    if (!reason) {
      return;
    }
    const quantityValue = Number(batchForm.quantity);
    const payload: SupplierBatchPayload = {
      model_name: batchForm.modelName.trim(),
      batch_code: batchForm.batchCode.trim(),
      unit_cost: unitCostValue,
      quantity: Number.isFinite(quantityValue) && quantityValue >= 0 ? quantityValue : 0,
      purchase_date: batchForm.purchaseDate,
    };

    const noteValue = batchForm.notes.trim();
    if (noteValue) {
      payload.notes = noteValue;
    }
    if (batchForm.storeId !== "") {
      payload.store_id = Number(batchForm.storeId);
    }
    if (batchForm.deviceId !== "") {
      payload.device_id = Number(batchForm.deviceId);
    }

    try {
      setError(null);
      if (batchEditingId) {
        await updateSupplierBatch(token, batchEditingId, payload, reason);
        setMessage("Lote actualizado correctamente.");
      } else {
        await createSupplierBatch(token, selectedSupplierId, payload, reason);
        setMessage("Lote registrado correctamente.");
      }
      resetBatchForm();
      await refreshBatches(selectedSupplierId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible guardar el lote del proveedor.");
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
          <button type="submit" className="btn btn--primary">
            {editingId ? "Actualizar proveedor" : "Agregar proveedor"}
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
                const lastEntry = historyLength > 0 ? supplier.history[historyLength - 1] : null;
                const lastHistory = lastEntry?.note ?? "—";
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
                        <button type="button" className="btn btn--link" onClick={() => handleEdit(supplier)}>
                          Editar
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleAddNote(supplier)}>
                          Nota
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleAdjustDebt(supplier)}>
                          Ajustar saldo
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleSelectBatches(supplier)}>
                          Lotes
                        </button>
                        <button type="button" className="btn btn--link" onClick={() => handleDelete(supplier)}>
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
      <div className="section-divider">
        <h3>Lotes y costos por proveedor</h3>
        {selectedSupplierId ? (
          <>
            <p className="muted-text">
              Gestiona los lotes registrados para <strong>{selectedSupplierName}</strong> y mantén actualizado el costo
              promedio de inventario.
            </p>
            <form className="form-grid" onSubmit={handleBatchSubmit}>
              <label>
                <span>Sucursal</span>
                <select
                  value={batchForm.storeId === "" ? "" : String(batchForm.storeId)}
                  onChange={(event) =>
                    updateBatchForm({
                      storeId: event.target.value === "" ? "" : Number(event.target.value),
                    })
                  }
                >
                  <option value="">Sin asignar</option>
                  {stores.map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>ID de dispositivo (opcional)</span>
                <input
                  type="number"
                  min={1}
                  value={batchForm.deviceId === "" ? "" : batchForm.deviceId}
                  onChange={(event) =>
                    updateBatchForm({
                      deviceId: event.target.value === "" ? "" : Number(event.target.value),
                    })
                  }
                  placeholder="Ej. 1024"
                />
              </label>
              <label>
                <span>Modelo</span>
                <input
                  value={batchForm.modelName}
                  onChange={(event) => updateBatchForm({ modelName: event.target.value })}
                  required
                />
              </label>
              <label>
                <span>Código de lote</span>
                <input
                  value={batchForm.batchCode}
                  onChange={(event) => updateBatchForm({ batchCode: event.target.value })}
                  required
                />
              </label>
              <label>
                <span>Costo unitario</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={batchForm.unitCost}
                  onChange={(event) => updateBatchForm({ unitCost: Number(event.target.value) })}
                  required
                />
              </label>
              <label>
                <span>Cantidad</span>
                <input
                  type="number"
                  min={0}
                  step="1"
                  value={batchForm.quantity}
                  onChange={(event) => updateBatchForm({ quantity: Number(event.target.value) })}
                />
              </label>
              <label>
                <span>Fecha de compra</span>
                <input
                  type="date"
                  value={batchForm.purchaseDate}
                  onChange={(event) => updateBatchForm({ purchaseDate: event.target.value })}
                  required
                />
              </label>
              <label className="wide">
                <span>Notas del lote</span>
                <textarea
                  value={batchForm.notes}
                  onChange={(event) => updateBatchForm({ notes: event.target.value })}
                  rows={2}
                  placeholder="Observaciones, acuerdos o condiciones especiales"
                />
              </label>
              <div className="actions-row wide">
                <button type="submit" className="btn btn--primary">
                  {batchEditingId ? "Actualizar lote" : "Registrar lote"}
                </button>
                {batchEditingId ? (
                  <button type="button" className="btn btn--ghost" onClick={resetBatchForm}>
                    Cancelar
                  </button>
                ) : null}
              </div>
            </form>
            {loadingBatches ? (
              <p className="muted-text">Cargando lotes registrados...</p>
            ) : batches.length === 0 ? (
              <p className="muted-text">Aún no se registran lotes para este proveedor.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Lote</th>
                      <th>Modelo</th>
                      <th>Fecha</th>
                      <th>Sucursal</th>
                      <th>ID dispositivo</th>
                      <th>Costo unitario</th>
                      <th>Cantidad</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batches.map((batch) => (
                      <tr key={batch.id}>
                        <td>{batch.batch_code}</td>
                        <td>{batch.model_name}</td>
                        <td>{batch.purchase_date}</td>
                        <td>{batch.store_id ? storeLookup.get(batch.store_id) ?? `#${batch.store_id}` : "—"}</td>
                        <td>{batch.device_id ?? "—"}</td>
                        <td>{currencyFormatter.format(batch.unit_cost)}</td>
                        <td>{batch.quantity}</td>
                        <td>
                          <div className="actions-row">
                            <button type="button" className="btn btn--link" onClick={() => handleBatchEdit(batch)}>
                              Editar
                            </button>
                            <button type="button" className="btn btn--link" onClick={() => handleBatchDelete(batch)}>
                              Eliminar
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <p className="muted-text">Selecciona un proveedor para administrar sus lotes y costos asociados.</p>
        )}
      </div>
    </section>
  );
}

export default Suppliers;
