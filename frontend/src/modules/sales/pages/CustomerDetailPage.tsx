import React from "react";
// [PACK23-CUSTOMERS-DETAIL-IMPORTS-START]
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { SalesCustomers } from "../../../services/sales";
import type { Customer } from "../../../services/sales";
import { required, emailish, phoneish } from "../utils/forms";
// [PACK23-CUSTOMERS-DETAIL-IMPORTS-END]
import { CustomerDetailCard } from "../components/customers";

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
    try {
      if (id) {
        const updated = await SalesCustomers.updateCustomer(id, partial);
        setData(updated);
      } else {
        const created = await SalesCustomers.createCustomer(partial as Omit<Customer, "id">);
        setData(created);
        // TODO: navegar a detalle created.id si el router lo soporta
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

  return (
    <div style={{ display: "grid", gap: 16, maxWidth: 600 }}>
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
