import { Fragment, useEffect, useMemo, useState, useCallback } from "react";

import type {
  WarrantyAssignment,
  WarrantyMetrics,
  WarrantyStatus,
  WarrantyClaim,
  WarrantyClaimType,
  WarrantyClaimPayload,
} from "@api/sales";
import type { Customer } from "@api/customers";
import type { Store } from "@api/stores";
import type { Device } from "@api/inventory";
import {
  createWarrantyClaim,
  getWarranty,
  getWarrantyMetrics,
  listWarranties,
  updateWarrantyClaimStatus,
} from "@api/sales";
import { listCustomers } from "@api/customers";
import { getDevices } from "@api/inventory";
import Button from "@components/ui/Button";
import Modal from "@components/ui/Modal";
import SidePanel from "../../repairs/components/SidePanel";
import type { RepairForm, RepairPartForm } from "../../../types/repairs";

const warrantyStatusLabels: Record<WarrantyStatus, string> = {
  SIN_GARANTIA: "Sin garantía",
  ACTIVA: "Activa",
  VENCIDA: "Vencida",
  RECLAMO: "Con reclamo",
  RESUELTA: "Resuelta",
};

const claimTypeLabels: Record<WarrantyClaimType, string> = {
  REPARACION: "Reparación",
  REEMPLAZO: "Reemplazo",
};

const claimStatusLabels = {
  ABIERTO: "Abierto",
  EN_PROCESO: "En proceso",
  RESUELTO: "Resuelto",
  CANCELADO: "Cancelado",
} as const;

type WarrantiesProps = {
  token: string;
  stores: Store[];
  defaultStoreId?: number | null;
};

type WarrantyFilters = {
  status?: WarrantyStatus | "TODAS";
  search: string;
};

type WarrantyClaimDialogProps = {
  token: string;
  stores: Store[];
  open: boolean;
  assignment: WarrantyAssignment | null;
  onClose: () => void;
  onRegistered: (updated: WarrantyAssignment) => void;
};

const initialRepairForm: RepairForm = {
  storeId: null,
  customerId: null,
  customerName: "",
  customerContact: "",
  technicianName: "",
  damageType: "",
  diagnosis: "",
  deviceModel: "",
  imei: "",
  deviceDescription: "",
  problemDescription: "",
  notes: "",
  estimatedCost: 0,
  depositAmount: 0,
  laborCost: 0,
  parts: [],
};

function WarrantyClaimDialog({
  token,
  stores,
  open,
  assignment,
  onClose,
  onRegistered,
}: WarrantyClaimDialogProps) {
  const [claimType, setClaimType] = useState<WarrantyClaimType>("REPARACION");
  const [notes, setNotes] = useState("");
  const [reason, setReason] = useState("Reclamo garantía");
  const [withRepairOrder, setWithRepairOrder] = useState(true);
  const [form, setForm] = useState<RepairForm>(initialRepairForm);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [customerSearch, setCustomerSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyAssignmentDefaults = useCallback(() => {
    if (!assignment) {
      setForm(initialRepairForm);
      return;
    }
    const saleStoreId = assignment.sale?.store_id ?? null;
    setForm({
      ...initialRepairForm,
      storeId: saleStoreId,
      customerId: assignment.sale?.customer_id ?? null,
      customerName: assignment.sale?.customer_name ?? "",
      deviceModel: assignment.device?.name ?? "",
      imei: assignment.device?.imei ?? assignment.serial_number ?? "",
      deviceDescription: assignment.device?.sku ?? "",
    });
  }, [assignment]);

  useEffect(() => {
    if (!open || !assignment) {
      return;
    }
    setClaimType("REPARACION");
    setNotes("");
    setReason("Reclamo garantía");
    setWithRepairOrder(true);
    applyAssignmentDefaults();
    setCustomers([]);
    setDevices([]);
    setCustomerSearch("");
  }, [open, assignment, applyAssignmentDefaults]);

  useEffect(() => {
    if (!open || !assignment) {
      return;
    }
    const options =
      customerSearch.trim().length >= 2
        ? { limit: 50, query: customerSearch.trim() }
        : { limit: 50 };
    listCustomers(token, options)
      .then(setCustomers)
      .catch(() => setCustomers([]));
  }, [open, assignment, token, customerSearch]);

  useEffect(() => {
    if (!open || !assignment?.sale?.store_id) {
      return;
    }
    getDevices(token, assignment.sale.store_id, { limit: 50 })
      .then(setDevices)
      .catch(() => setDevices([]));
  }, [open, assignment, token]);

  const handleFormChange = (updates: Partial<RepairForm>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  };

  const handlePartChange = (index: number, updates: Partial<RepairPartForm>) => {
    setForm((prev) => ({
      ...prev,
      parts: prev.parts.map((part, idx) => (idx === index ? { ...part, ...updates } : part)),
    }));
  };

  const handleAddPart = () => {
    setForm((prev) => ({
      ...prev,
      parts: [
        ...prev.parts,
        { deviceId: null, quantity: 1, unitCost: 0, source: "STOCK", partName: "" },
      ],
    }));
  };

  const handleRemovePart = (index: number) => {
    setForm((prev) => ({
      ...prev,
      parts: prev.parts.filter((_, idx) => idx !== index),
    }));
  };

  const submitClaim = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!assignment) {
      return;
    }
    const normalizedReason = reason.trim();
    if (normalizedReason.length < 5) {
      setError("Ingresa un motivo corporativo de al menos 5 caracteres.");
      return;
    }
    const payload: WarrantyClaimPayload = {
      claim_type: claimType,
      notes: notes.trim() || null,
    };
    if (withRepairOrder) {
      const storeId = form.storeId ?? assignment.sale?.store_id ?? null;
      if (!storeId) {
        setError("Selecciona la sucursal responsable de la reparación.");
        return;
      }
      if (!form.technicianName.trim() || !form.damageType.trim()) {
        setError("Completa técnico y tipo de daño para registrar la reparación.");
        return;
      }
      payload.repair_order = {
        store_id: storeId,
        customer_id: form.customerId ?? null,
        customer_name: form.customerName?.trim() || null,
        customer_contact: form.customerContact?.trim() || null,
        technician_name: form.technicianName.trim(),
        damage_type: form.damageType.trim(),
        diagnosis: form.diagnosis?.trim() || "",
        problem_description: form.problemDescription?.trim() || "",
        estimated_cost: form.estimatedCost ?? 0,
        deposit_amount: form.depositAmount ?? 0,
        ...(form.deviceModel?.trim() ? { device_model: form.deviceModel.trim() } : {}),
        ...(form.imei?.trim() ? { imei: form.imei.trim() } : {}),
        ...(form.deviceDescription?.trim()
          ? { device_description: form.deviceDescription.trim() }
          : {}),
        ...(form.notes?.trim() ? { notes: form.notes.trim() } : {}),
        labor_cost: form.laborCost ?? 0,
        parts: form.parts.map((part) => ({
          ...(part.deviceId ? { device_id: part.deviceId } : {}),
          ...(part.partName?.trim() ? { part_name: part.partName.trim() } : {}),
          source: part.source,
          quantity: part.quantity,
          unit_cost: part.unitCost ?? 0,
        })),
      };
    }

    try {
      setLoading(true);
      setError(null);
      const updated = await createWarrantyClaim(token, assignment.id, payload, normalizedReason);
      onRegistered(updated);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar el reclamo";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const hasOpenClaim = assignment?.claims.some(
    (claim) => claim.status === "ABIERTO" || claim.status === "EN_PROCESO",
  );

  return (
    <Modal open={open} onClose={loading ? () => {} : onClose} title="Registrar reclamo de garantía">
      {assignment ? (
        <form onSubmit={submitClaim} className="warranty-claim-form">
          <div className="warranty-claim-grid">
            <section className="warranty-claim-section">
              <header className="warranty-claim-header">
                <h3>Detalle de la garantía</h3>
                <p className="muted-text">
                  Venta #{assignment.sale?.id ?? "-"} · {assignment.device?.name ?? "Dispositivo"} ·
                  Serie {assignment.serial_number ?? "N/D"}
                </p>
              </header>
              <label className="form-field">
                Tipo de reclamo
                <select
                  value={claimType}
                  onChange={(event) => setClaimType(event.target.value as WarrantyClaimType)}
                >
                  {(Object.keys(claimTypeLabels) as WarrantyClaimType[]).map((option) => (
                    <option key={option} value={option}>
                      {claimTypeLabels[option]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                Descripción
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={3}
                  placeholder="Describe el problema reportado"
                />
              </label>
              <label className="form-field">
                Motivo corporativo
                <input
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  placeholder="Motivo registrado en auditoría"
                />
                <span className="muted-text">Se enviará como cabecera X-Reason.</span>
              </label>
              <label className="form-checkbox">
                <input
                  type="checkbox"
                  checked={withRepairOrder}
                  onChange={(event) => setWithRepairOrder(event.target.checked)}
                  disabled={hasOpenClaim}
                />
                <span>Generar orden de reparación usando el formulario de reparaciones</span>
              </label>
              {hasOpenClaim ? (
                <p className="alert info">
                  Existe un reclamo abierto. Completa su resolución antes de crear otro.
                </p>
              ) : null}
              {error ? <p className="alert error">{error}</p> : null}
              <div className="dialog-actions">
                <Button type="button" variant="ghost" onClick={onClose} disabled={loading}>
                  Cancelar
                </Button>
                <Button type="submit" variant="primary" disabled={loading || hasOpenClaim}>
                  {loading ? "Guardando…" : "Registrar reclamo"}
                </Button>
              </div>
            </section>
            {withRepairOrder ? (
              <section className="warranty-claim-section">
                <SidePanel
                  stores={stores}
                  selectedStoreId={form.storeId}
                  form={form}
                  customers={customers}
                  devices={devices}
                  customerSearch={customerSearch}
                  onCustomerSearchChange={setCustomerSearch}
                  onStoreChange={(storeId) => handleFormChange({ storeId })}
                  onFormChange={handleFormChange}
                  onSubmit={(event) => event.preventDefault()}
                  onReset={applyAssignmentDefaults}
                  onAddPart={handleAddPart}
                  onRemovePart={handleRemovePart}
                  onPartChange={handlePartChange}
                />
              </section>
            ) : null}
          </div>
        </form>
      ) : (
        <p>No se encontró la garantía seleccionada.</p>
      )}
    </Modal>
  );
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return "-";
  const date = new Date(iso);
  return date.toLocaleDateString("es-HN");
}

function formatRemaining(days: number, isExpired: boolean) {
  if (isExpired) {
    return "Vencida";
  }
  if (days <= 0) {
    return "Expira hoy";
  }
  return `${days} días`;
}

export default function Warranties({ token, stores, defaultStoreId = null }: WarrantiesProps) {
  const [assignments, setAssignments] = useState<WarrantyAssignment[]>([]);
  const [metrics, setMetrics] = useState<WarrantyMetrics | null>(null);
  const [filters, setFilters] = useState<WarrantyFilters>({ status: "ACTIVA", search: "" });
  const [selectedStoreId, setSelectedStoreId] = useState<number | null>(defaultStoreId);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [claimAssignment, setClaimAssignment] = useState<WarrantyAssignment | null>(null);
  const [claimDialogOpen, setClaimDialogOpen] = useState(false);

  const statusOptions = useMemo(
    () => ["TODAS", "ACTIVA", "VENCIDA", "RECLAMO", "RESUELTA"] as const,
    [],
  );

  const refreshMetrics = async (storeId: number | null) => {
    try {
      const data = await getWarrantyMetrics(token, { ...(storeId ? { store_id: storeId } : {}) });
      setMetrics(data);
    } catch {
      setMetrics(null);
    }
  };

  const refreshAssignments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listWarranties(token, {
        ...(selectedStoreId ? { store_id: selectedStoreId } : {}),
        ...(filters.status && filters.status !== "TODAS" ? { status: filters.status } : {}),
        ...(filters.search ? { q: filters.search.trim() } : {}),
      });
      setAssignments(response);
      await refreshMetrics(selectedStoreId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible cargar las garantías";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshAssignments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedStoreId, filters.status, filters.search]);

  const handleOpenClaim = async (assignment: WarrantyAssignment) => {
    try {
      const refreshed = await getWarranty(token, assignment.id);
      setClaimAssignment(refreshed);
    } catch {
      setClaimAssignment(assignment);
    }
    setClaimDialogOpen(true);
  };

  const handleAssignmentUpdated = (updated: WarrantyAssignment) => {
    setAssignments((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    void refreshMetrics(selectedStoreId);
  };

  const resolveClaim = async (claimId: number) => {
    try {
      const updated = await updateWarrantyClaimStatus(
        token,
        claimId,
        { status: "RESUELTO" },
        "Resolver reclamo",
      );
      handleAssignmentUpdated(updated);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible actualizar el reclamo";
      setError(message);
    }
  };

  const resolveClaimsSummary = (claims: WarrantyClaim[]): string => {
    if (!claims.length) {
      return "Sin reclamos";
    }
    const latest = [...claims].sort(
      (a, b) => new Date(b.opened_at).getTime() - new Date(a.opened_at).getTime(),
    )[0];
    if (!latest) return "Sin reclamos";
    return `${claimStatusLabels[latest.status]} · ${formatDate(latest.opened_at)}`;
  };

  return (
    <section className="panel">
      <header className="panel__header">
        <h2>Garantías vinculadas a ventas</h2>
        <p className="panel__subtitle">
          Controla los periodos de cobertura, registra reclamos y documenta las resoluciones desde
          un único panel.
        </p>
      </header>
      <div className="panel__body">
        <div className="warranty-toolbar">
          <label className="form-field">
            Sucursal
            <select
              value={selectedStoreId ?? ""}
              onChange={(event) =>
                setSelectedStoreId(event.target.value ? Number(event.target.value) : null)
              }
            >
              <option value="">Todas</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            Estado
            <select
              value={filters.status ?? "TODAS"}
              onChange={(event) =>
                setFilters((prev) => ({
                  ...prev,
                  status: event.target.value as WarrantyStatus | "TODAS",
                }))
              }
            >
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option === "TODAS" ? "Todas" : warrantyStatusLabels[option]}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field warranty-toolbar__search">
            Buscar
            <input
              value={filters.search}
              onChange={(event) => setFilters((prev) => ({ ...prev, search: event.target.value }))}
              placeholder="Cliente, dispositivo, serie"
            />
          </label>
          <Button variant="ghost" onClick={refreshAssignments} disabled={loading}>
            Actualizar
          </Button>
        </div>

        {metrics ? (
          <div className="warranty-metrics">
            <article className="metric-card">
              <h3>Total activas</h3>
              <p>{metrics.active_assignments}</p>
              <span className="muted-text">Cobertura vigente</span>
            </article>
            <article className="metric-card">
              <h3>Por expirar</h3>
              <p>{metrics.expiring_soon}</p>
              <span className="muted-text">Próximos 30 días</span>
            </article>
            <article className="metric-card">
              <h3>Reclamos abiertos</h3>
              <p>{metrics.claims_open}</p>
              <span className="muted-text">Pendientes de resolución</span>
            </article>
            <article className="metric-card">
              <h3>Resueltas</h3>
              <p>{metrics.claims_resolved}</p>
              <span className="muted-text">
                Cobertura promedio {Math.round(metrics.average_coverage_days)} días
              </span>
            </article>
          </div>
        ) : null}

        {error ? <div className="alert error">{error}</div> : null}
        {loading ? <div className="alert info">Cargando garantías…</div> : null}

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Dispositivo</th>
                <th scope="col">Venta</th>
                <th scope="col">Cobertura</th>
                <th scope="col">Estado</th>
                <th scope="col">Reclamos</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {assignments.length === 0 ? (
                <tr>
                  <td colSpan={6} className="warranty-table__empty">
                    No se encontraron garantías con los filtros actuales.
                  </td>
                </tr>
              ) : (
                assignments.map((assignment) => (
                  <tr key={assignment.id}>
                    <td>
                      <strong>{assignment.device?.name ?? "Dispositivo"}</strong>
                      <div className="muted-text">Serie {assignment.serial_number ?? "N/D"}</div>
                    </td>
                    <td>
                      <div>#{assignment.sale?.id ?? "-"}</div>
                      <div className="muted-text">{formatDate(assignment.activation_date)}</div>
                    </td>
                    <td>
                      <div>{assignment.coverage_months} meses</div>
                      <div className="muted-text">
                        {formatRemaining(assignment.remaining_days, assignment.is_expired)}
                      </div>
                    </td>
                    <td>
                      <strong>{warrantyStatusLabels[assignment.status]}</strong>
                    </td>
                    <td>
                      <div>{resolveClaimsSummary(assignment.claims)}</div>
                    </td>
                    <td>
                      <div className="warranty-actions">
                        {(() => {
                          const hasPendingClaim = assignment.claims.some(
                            (claim) => claim.status === "ABIERTO" || claim.status === "EN_PROCESO",
                          );
                          return (
                            <Button
                              variant="primary"
                              onClick={() => handleOpenClaim(assignment)}
                              disabled={hasPendingClaim}
                            >
                              {hasPendingClaim ? "Reclamo en curso" : "Registrar reclamo"}
                            </Button>
                          );
                        })()}
                        {assignment.claims.length > 0
                          ? assignment.claims.map((claim) => (
                              <Fragment key={claim.id}>
                                {claim.status !== "RESUELTO" && claim.status !== "CANCELADO" ? (
                                  <Button
                                    variant="ghost"
                                    onClick={() => void resolveClaim(claim.id)}
                                  >
                                    Marcar resuelto
                                  </Button>
                                ) : null}
                              </Fragment>
                            ))
                          : null}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <WarrantyClaimDialog
        token={token}
        stores={stores}
        open={claimDialogOpen}
        assignment={claimAssignment}
        onClose={() => setClaimDialogOpen(false)}
        onRegistered={handleAssignmentUpdated}
      />
    </section>
  );
}
