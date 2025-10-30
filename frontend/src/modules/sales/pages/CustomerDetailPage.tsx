import React from "react";
// [PACK23-CUSTOMERS-DETAIL-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { SalesCustomers } from "../../../services/sales";
import type { Customer } from "../../../services/sales";
import { required, emailish, phoneish } from "../utils/forms";
// [PACK23-CUSTOMERS-DETAIL-IMPORTS-END]
import { CustomerDetailCard } from "../components/customers";
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@/ui/Skeleton";
// [PACK25-SKELETON-USE-END]
import { readQueue } from "@/services/offline";
import type { ApiError } from "@/services/http";
import { flushOffline, safeCreateCustomer, safeUpdateCustomer } from "../utils/offline";

function resolveRemoteErrorMessage(error: unknown): string {
  if (!error) {
    return "Ocurrió un error al guardar. Revisa la información e inténtalo de nuevo.";
  }
  const apiError = error as ApiError | undefined;
  const detail = apiError?.details as { detail?: string; message?: string } | undefined;
  if (typeof detail?.detail === "string" && detail.detail.trim().length > 0) {
    return detail.detail;
  }
  if (typeof detail?.message === "string" && detail.message.trim().length > 0) {
    return detail.message;
  }
  if (apiError && typeof apiError.message === "string" && apiError.message.trim().length > 0) {
    return apiError.message;
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return "Ocurrió un error al guardar. Revisa la información e inténtalo de nuevo.";
}

type CustomerProfile = {
  id?: string;
  name: string;
  email?: string;
  phone?: string;
  tier?: string;
  tags?: string[];
  notes?: string;
};

const emptyProfile: CustomerProfile = { id: undefined, name: "", email: "", phone: "", tier: "", notes: "" };

export function CustomerDetailPage() {
  // [PACK23-CUSTOMERS-DETAIL-STATE-START]
  const { id } = useParams(); // si no hay id -> crear
  const [data, setData] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string,string>>({});
  // [PACK23-CUSTOMERS-DETAIL-STATE-END]
  const [form, setForm] = useState<CustomerProfile>(emptyProfile);
  const [pendingOffline, setPendingOffline] = useState(0);
  const [flushing, setFlushing] = useState(false);
  const [flushMessage, setFlushMessage] = useState<string | null>(null);
  const [offlineNotice, setOfflineNotice] = useState<string | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setData(null);
      setForm(emptyProfile);
      return;
    }
    (async () => {
      setLoading(true);
      try {
        const customer = await SalesCustomers.getCustomer(id);
        setData(customer);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  useEffect(() => {
    if (data) {
      setForm({
        id: String(data.id),
        name: data.name,
        email: data.email,
        phone: data.phone,
        tier: data.tier,
        tags: data.tags,
        notes: data.notes,
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
    const e: Record<string,string> = {};
    if (!required(d.name)) e.name = "Requerido";
    if (!emailish(d.email)) e.email = "Email inválido";
    if (!phoneish(d.phone)) e.phone = "Teléfono inválido";
    return e;
  }

  async function onSave(partial: Partial<Customer>) {
    const e = validate(partial);
    setErrors(e);
    if (Object.keys(e).length) return;

    setSaving(true);
    setRemoteError(null);
    setOfflineNotice(null);
    try {
      if (id) {
        const result = await safeUpdateCustomer(id, partial);
        if (result.status === "ok") {
          setData(result.data);
        } else if (result.status === "queued") {
          setOfflineNotice("Cambios guardados offline. Reintenta cuando vuelvas a tener conexión.");
        } else {
          setRemoteError(resolveRemoteErrorMessage(result.error));
        }
      } else {
        const result = await safeCreateCustomer(partial as Omit<Customer, "id">);
        if (result.status === "ok") {
          setData(result.data);
        } else if (result.status === "queued") {
          setOfflineNotice("Cliente encolado offline. Reintenta sincronizar más tarde.");
        } else {
          setRemoteError(resolveRemoteErrorMessage(result.error));
        }
        // TODO: navegar a detalle created.id si el router lo soporta
      }
      if (typeof window !== "undefined") {
        setPendingOffline(readQueue().length);
      }
    } finally {
      setSaving(false);
    }
  }
  // [PACK23-CUSTOMERS-DETAIL-SAVE-END]

  const isCreateMode = !id;
  const detailCardValue: CustomerProfile = data ?? {
    ...form,
    id: form.id ?? "nuevo",
  };

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
          id: detailCardValue.id ?? "nuevo",
          name: detailCardValue.name,
          email: detailCardValue.email,
          phone: detailCardValue.phone,
          tier: detailCardValue.tier,
          tags: detailCardValue.tags,
          notes: detailCardValue.notes,
        }}
      />
    );
  }, [data, detailCardValue, id, loading]);

  return (
    <div style={{ display: "grid", gap: 16, maxWidth: 600 }}>
      {pendingOffline > 0 ? (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ color: "#fbbf24" }}>Pendientes offline: {pendingOffline}</span>
          <button
            type="button"
            onClick={handleFlush}
            disabled={flushing}
            style={{ padding: "6px 12px", borderRadius: 8, border: "none", background: "rgba(56,189,248,0.16)", color: "#e0f2fe" }}
          >
            {flushing ? "Reintentando…" : "Reintentar pendientes"}
          </button>
        </div>
      ) : null}
      {flushMessage ? <div style={{ color: "#9ca3af", fontSize: 12 }}>{flushMessage}</div> : null}
      {offlineNotice ? <div style={{ color: "#fbbf24", fontSize: 13 }}>{offlineNotice}</div> : null}
      {remoteError ? <div style={{ color: "#f87171", fontSize: 13 }}>{remoteError}</div> : null}
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
        style={{ display: "grid", gap: 12 }}
      >
        <div>
          <label style={{ display: "block", marginBottom: 4 }}>Nombre</label>
          <input
            value={form.name}
            onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
            style={{ padding: 8, borderRadius: 8, width: "100%" }}
            disabled={loading || saving}
          />
          {errors.name && <span style={{ color: "#f87171", fontSize: 12 }}>{errors.name}</span>}
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 4 }}>Email</label>
          <input
            value={form.email ?? ""}
            onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
            style={{ padding: 8, borderRadius: 8, width: "100%" }}
            disabled={loading || saving}
            type="email"
          />
          {errors.email && <span style={{ color: "#f87171", fontSize: 12 }}>{errors.email}</span>}
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 4 }}>Teléfono</label>
          <input
            value={form.phone ?? ""}
            onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))}
            style={{ padding: 8, borderRadius: 8, width: "100%" }}
            disabled={loading || saving}
          />
          {errors.phone && <span style={{ color: "#f87171", fontSize: 12 }}>{errors.phone}</span>}
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 4 }}>Tier</label>
          <input
            value={form.tier ?? ""}
            onChange={(event) => setForm((prev) => ({ ...prev, tier: event.target.value }))}
            style={{ padding: 8, borderRadius: 8, width: "100%" }}
            disabled={loading || saving}
          />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 4 }}>Notas</label>
          <textarea
            value={form.notes ?? ""}
            onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
            style={{ padding: 8, borderRadius: 8, minHeight: 100, width: "100%" }}
            disabled={loading || saving}
          />
        </div>
        <button
          type="submit"
          style={{ padding: "10px 16px", borderRadius: 8, background: "#38bdf8", color: "#0f172a", border: "none", fontWeight: 600 }}
          disabled={saving || loading}
        >
          {saving ? "Guardando…" : isCreateMode ? "Crear cliente" : "Actualizar cliente"}
        </button>
      </form>
      <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700 }}>Historial de compras</div>
        {/* TODO(wire) tabla de ventas del cliente */}
      </div>
    </div>
  );
}
