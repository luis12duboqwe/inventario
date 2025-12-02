import React from "react";
// [PACK23-CUSTOMERS-DETAIL-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { SalesCustomers } from "../../../services/sales";
import type { Customer } from "../../../services/sales";
import { required, emailish, phoneish } from "../utils/forms";
// [PACK23-CUSTOMERS-DETAIL-IMPORTS-END]
import { CustomerDetailCard } from "../components/customers";
// [PACK26-CUSTOMERS-DETAIL-PERMS-START]
import { useAuthz, PERMS, RequirePerm } from "../../../auth/useAuthz";
import { logUI } from "../../../services/audit";
// [PACK26-CUSTOMERS-DETAIL-PERMS-END]
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@components/ui/Skeleton";
// [PACK25-SKELETON-USE-END]
import { readQueue } from "@/services/offline";
import { flushOffline, safeCreateCustomer, safeUpdateCustomer } from "../utils/offline";

type CustomerProfile = {
  id?: string;
  name: string;
  email: string;
  phone: string;
  tier: string;
  tags: string[];
  notes: string;
};

const emptyProfile: CustomerProfile = {
  name: "",
  email: "",
  phone: "",
  tier: "",
  notes: "",
  tags: [],
};

export function CustomerDetailPage() {
  const { can, user } = useAuthz();
  const canView = can(PERMS.CUSTOMER_LIST);
  const canCreate = can(PERMS.CUSTOMER_CREATE);
  const canEdit = can(PERMS.CUSTOMER_EDIT);
  // [PACK23-CUSTOMERS-DETAIL-STATE-START]
  const { id } = useParams(); // si no hay id -> crear
  const [data, setData] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  // [PACK23-CUSTOMERS-DETAIL-STATE-END]
  const [form, setForm] = useState<CustomerProfile>(emptyProfile);
  const [pendingOffline, setPendingOffline] = useState(0);
  const [flushing, setFlushing] = useState(false);
  const [flushMessage, setFlushMessage] = useState<string | null>(null);
  const [offlineNotice, setOfflineNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setData(null);
      setForm({ ...emptyProfile });
      return;
    }
    (async () => {
      if (!canView) {
        setData(null);
        return;
      }
      setLoading(true);
      try {
        const customer = await SalesCustomers.getCustomer(id);
        setData(customer);
      } finally {
        setLoading(false);
      }
    })();
  }, [id, canView]);

  useEffect(() => {
    if (data) {
      setForm({
        id: String(data.id),
        name: data.name,
        email: data.email ?? "",
        phone: data.phone ?? "",
        tier: data.tier ?? "",
        tags: Array.isArray(data.tags) ? [...data.tags] : [],
        notes: data.notes ?? "",
      });
    }
  }, [data]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, [data]);

  // [PACK23-CUSTOMERS-DETAIL-SAVE-START]
  function validate(d: Partial<Customer>) {
    const e: Record<string, string> = {};
    if (!required(d.name)) e.name = "Requerido";
    if (!emailish(d.email)) e.email = "Email inválido";
    if (!phoneish(d.phone)) e.phone = "Teléfono inválido";
    return e;
  }

  async function onSave(partial: Partial<Customer>) {
    if (id && !canEdit) return;
    if (!id && !canCreate) return;
    const e = validate(partial);
    setErrors(e);
    if (Object.keys(e).length) return;

    setSaving(true);
    try {
      if (id) {
        const updated = await safeUpdateCustomer(id, partial); // [PACK37-frontend]
        if (updated) {
          setData(updated);
          setOfflineNotice(null);
          await logUI({
            ts: Date.now(),
            userId: user?.id ?? null,
            module: "CUSTOMERS",
            action: "update",
            ...(id ? { entityId: id } : {}),
          }); // [PACK37-frontend]
        } else {
          setOfflineNotice("Cambios guardados offline. Reintenta cuando vuelvas a tener conexión."); // [PACK37-frontend]
        }
      } else {
        const created = await safeCreateCustomer(partial as Omit<Customer, "id">); // [PACK37-frontend]
        if (created) {
          setData(created);
          setOfflineNotice(null);
          await logUI({
            ts: Date.now(),
            userId: user?.id ?? null,
            module: "CUSTOMERS",
            action: "create",
            ...(created?.id ? { entityId: String(created.id) } : {}),
          }); // [PACK37-frontend]
          // TODO: navegar a detalle created.id si el router lo soporta
        } else {
          setOfflineNotice("Cliente encolado offline. Reintenta sincronizar más tarde."); // [PACK37-frontend]
        }
      }
      if (typeof window !== "undefined") {
        setPendingOffline(readQueue().length); // [PACK37-frontend]
      }
    } finally {
      setSaving(false);
    }
  }
  // [PACK23-CUSTOMERS-DETAIL-SAVE-END]

  const isCreateMode = !id;
  const actionPerm = isCreateMode ? PERMS.CUSTOMER_CREATE : PERMS.CUSTOMER_EDIT;
  const detailCardValueMemo: CustomerProfile = useMemo(() => {
    if (data) {
      return {
        id: String(data.id),
        name: data.name,
        email: data.email ?? "",
        phone: data.phone ?? "",
        tier: data.tier ?? "",
        tags: Array.isArray(data.tags) ? [...data.tags] : [],
        notes: data.notes ?? "",
      };
    }
    return { ...form };
  }, [data, form]);

  // [PACK26-CUSTOMERS-DETAIL-GUARD-START]
  const unauthorizedView = Boolean(id) && !canView;
  const unauthorizedCreate = !id && !canCreate;
  const unauthorized = unauthorizedView || unauthorizedCreate;
  // [PACK26-CUSTOMERS-DETAIL-GUARD-END]

  const handleFlush = useCallback(async () => {
    setFlushing(true);
    try {
      const result = await flushOffline();
      setPendingOffline(result.pending);
      setFlushMessage(`Reintentadas: ${result.flushed}. Pendientes: ${result.pending}.`);
    } catch {
      setFlushMessage("No fue posible sincronizar los cambios. Intenta más tarde.");
    } finally {
      setFlushing(false);
    }
  }, []);

  const headerSection = useMemo(() => {
    if (Boolean(id) && loading && !data) {
      return <Skeleton lines={6} />;
    }
    return (
      <CustomerDetailCard
        value={{
          id: detailCardValueMemo.id ?? "nuevo",
          name: detailCardValueMemo.name,
          ...(detailCardValueMemo.email ? { email: detailCardValueMemo.email } : {}),
          ...(detailCardValueMemo.phone ? { phone: detailCardValueMemo.phone } : {}),
          ...(detailCardValueMemo.tier ? { tier: detailCardValueMemo.tier } : {}),
          ...(detailCardValueMemo.tags.length ? { tags: detailCardValueMemo.tags } : {}),
          ...(detailCardValueMemo.notes ? { notes: detailCardValueMemo.notes } : {}),
        }}
      />
    );
  }, [data, detailCardValueMemo, id, loading]);

  return (
    <div className="customer-detail-container customer-detail-container-limited">
      {unauthorized ? (
        <div>No autorizado</div>
      ) : (
        <>
          {pendingOffline > 0 ? (
            <div className="customer-detail-offline-bar">
              <span className="customer-detail-offline-text">
                Pendientes offline: {pendingOffline}
              </span>
              <button
                type="button"
                onClick={handleFlush}
                disabled={flushing}
                className="customers-list-button customers-list-button-secondary customer-detail-retry-btn"
              >
                {flushing ? "Reintentando…" : "Reintentar pendientes"}
              </button>
            </div>
          ) : null}
          {flushMessage ? (
            <div className="customer-detail-flush-message">{flushMessage}</div>
          ) : null}
          {offlineNotice ? (
            <div className="customer-detail-offline-notice">{offlineNotice}</div>
          ) : null}
          {headerSection}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              onSave({
                name: form.name,
                email: form.email,
                phone: form.phone,
                tier: form.tier,
                notes: form.notes,
                tags: form.tags,
              });
            }}
            className="customer-detail-grid"
          >
            <div className="customer-detail-info-group">
              <label htmlFor="customer-name" className="customer-detail-label">
                Nombre
              </label>
              <input
                id="customer-name"
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                className="customer-detail-input"
                disabled={loading || saving}
              />
              {errors.name && <span className="customer-detail-error">{errors.name}</span>}
            </div>
            <div className="customer-detail-info-group">
              <label htmlFor="customer-email" className="customer-detail-label">
                Email
              </label>
              <input
                id="customer-email"
                value={form.email ?? ""}
                onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
                className="customer-detail-input"
                disabled={loading || saving}
                type="email"
              />
              {errors.email && <span className="customer-detail-error">{errors.email}</span>}
            </div>
            <div className="customer-detail-info-group">
              <label htmlFor="customer-phone" className="customer-detail-label">
                Teléfono
              </label>
              <input
                id="customer-phone"
                value={form.phone ?? ""}
                onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))}
                className="customer-detail-input"
                disabled={loading || saving}
              />
              {errors.phone && <span className="customer-detail-error">{errors.phone}</span>}
            </div>
            <div className="customer-detail-info-group">
              <label htmlFor="customer-tier" className="customer-detail-label">
                Tier
              </label>
              <input
                id="customer-tier"
                value={form.tier ?? ""}
                onChange={(event) => setForm((prev) => ({ ...prev, tier: event.target.value }))}
                className="customer-detail-input"
                disabled={loading || saving}
              />
            </div>
            <div className="customer-detail-info-group">
              <label htmlFor="customer-notes" className="customer-detail-label">
                Notas
              </label>
              <textarea
                id="customer-notes"
                value={form.notes ?? ""}
                onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
                className="customer-detail-textarea"
                disabled={loading || saving}
              />
            </div>
            <RequirePerm perm={actionPerm} fallback={null}>
              <button
                type="submit"
                className="customers-list-button customers-list-button-primary customer-detail-submit-btn"
                disabled={saving || loading}
              >
                {saving ? "Guardando…" : isCreateMode ? "Crear cliente" : "Actualizar cliente"}
              </button>
            </RequirePerm>
          </form>
          <div className="customer-detail-card">
            <div className="customer-detail-history-title">Historial de compras</div>
            {/* TODO(wire) tabla de ventas del cliente */}
          </div>
        </>
      )}
    </div>
  );
}

export default CustomerDetailPage;
