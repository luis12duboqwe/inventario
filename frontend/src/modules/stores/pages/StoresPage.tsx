import { useEffect, useMemo, useState } from "react";
import { MapPin, Building2, Hash, Clock, CheckCircle2 } from "lucide-react";
import ModuleHeader from "../../../shared/components/ModuleHeader";
import TextField from "../../../shared/components/ui/TextField";
import Button from "../../../shared/components/ui/Button";
import { useDashboard } from "../../dashboard/context/DashboardContext";
import { createStore, updateStore, type Store, type StoreCreateInput, type StoreUpdateInput } from "../../../api";

function StoresPage() {
  const { token, currentUser, pushToast, refreshStores, stores } = useDashboard();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [address, setAddress] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [isActive, setIsActive] = useState(true);
  const [reason, setReason] = useState("");

  const canManage = useMemo(() => {
    const roles = currentUser?.roles ?? [];
    return roles.some((r) => r.name === "ADMIN" || r.name === "GERENTE");
  }, [currentUser?.roles]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        await refreshStores();
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible cargar las sucursales";
        setError(message);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [refreshStores]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canManage) {
      setError("No cuentas con permisos para crear sucursales.");
      return;
    }
    const trimmedReason = reason.trim();
    if (trimmedReason.length < 5) {
      setError("Indica un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    if (name.trim().length < 3) {
      setError("El nombre debe tener al menos 3 caracteres.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      if (editingId) {
        const payload: StoreUpdateInput = {
          name: name.trim() || undefined,
          code: code.trim() || undefined,
          address: address.trim() || undefined,
          is_active: isActive,
          timezone: timezone.trim() || undefined,
        };
        const updated = await updateStore(token, editingId, payload, trimmedReason);
        pushToast({ message: `Sucursal "${updated.name}" actualizada`, variant: "success" });
      } else {
        const payload: StoreCreateInput = {
          name: name.trim(),
          code: code.trim() || undefined,
          address: address.trim() || undefined,
          is_active: isActive,
          timezone: timezone.trim() || "UTC",
        };
        const created = await createStore(token, payload, trimmedReason);
        pushToast({ message: `Sucursal "${created.name}" creada`, variant: "success" });
      }
      await refreshStores();
      // Limpiar formulario
      setEditingId(null);
      setName("");
      setCode("");
      setAddress("");
      setTimezone("UTC");
      setIsActive(true);
      setReason("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible guardar la sucursal";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (store: Store) => {
    setEditingId(store.id);
    setName(store.name ?? "");
    setCode(store.code ?? "");
    setAddress(store.location ?? "");
    setTimezone(store.timezone ?? "UTC");
    setIsActive((store.status ?? "").toLowerCase() !== "inactiva");
    setReason("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setName("");
    setCode("");
    setAddress("");
    setTimezone("UTC");
    setIsActive(true);
    setReason("");
  };

  return (
    <div className="module-content">
      <ModuleHeader
        icon={<MapPin aria-hidden="true" />}
        title="Sucursales"
        subtitle="Alta y administración de sucursales corporativas"
        status={canManage ? "ok" : "warning"}
        statusLabel={canManage ? "Administración disponible" : "Solo lectura"}
      />

      <div className="section-scroll">
        <div className="section-grid">
          <section className="card">
            <header className="card__header">
              <h3>Nueva sucursal</h3>
              <p>Completa los campos y guarda con un motivo corporativo.</p>
            </header>
            <form className="card__body form-grid" onSubmit={handleSubmit}>
              <TextField
                label="Nombre"
                placeholder="Nombre de la sucursal"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                leadingIcon={<Building2 size={16} />}
              />
              <TextField
                label="Código"
                placeholder="SUC-001"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                leadingIcon={<Hash size={16} />}
              />
              <TextField
                label="Dirección"
                placeholder="Calle, número, colonia, ciudad"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
              <TextField
                label="Zona horaria"
                placeholder="UTC, America/Mexico_City, etc."
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                leadingIcon={<Clock size={16} />}
              />
              <label className="ui-field checkbox">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                <span>Activa</span>
              </label>
              <TextField
                label="Motivo corporativo (X-Reason)"
                placeholder="Describe el motivo de la creación"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                helperText="Usa solo caracteres ASCII; mínimo 5 caracteres"
              />
              <div className="form-actions">
                <Button type="submit" variant="primary" disabled={loading || !canManage} leadingIcon={<CheckCircle2 size={16} />}>
                  {loading ? (editingId ? "Actualizando…" : "Guardando…") : (editingId ? "Actualizar sucursal" : "Guardar sucursal")}
                </Button>
                {editingId ? (
                  <Button type="button" variant="ghost" onClick={cancelEdit} disabled={loading}>
                    Cancelar edición
                  </Button>
                ) : null}
              </div>
              {error ? <div className="alert error" role="alert">{error}</div> : null}
            </form>
          </section>

          <section className="card">
            <header className="card__header">
              <h3>Listado de sucursales</h3>
              <p>Resumen básico de sucursales existentes.</p>
            </header>
            <div className="card__body">
              {loading && stores.length === 0 ? (
                <div className="loading-overlay" role="status" aria-live="polite">
                  <span className="spinner" aria-hidden="true" />
                  <span>Cargando sucursales…</span>
                </div>
              ) : null}
              {stores.length === 0 ? (
                <p>No hay sucursales registradas aún.</p>
              ) : (
                <div className="table-responsive">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Nombre</th>
                        <th>Código</th>
                        <th>Estatus</th>
                        <th>Zona horaria</th>
                        <th>Valor inventario</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stores.map((s) => (
                        <tr key={s.id} onClick={() => startEdit(s)} style={{ cursor: "pointer" }} aria-label={`Editar ${s.name}`}>
                          <td>{s.id}</td>
                          <td>{s.name}</td>
                          <td>{s.code}</td>
                          <td>{s.status}</td>
                          <td>{s.timezone}</td>
                          <td>{new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }).format(s.inventory_value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default StoresPage;
