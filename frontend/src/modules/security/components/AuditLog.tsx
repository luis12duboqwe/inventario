import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AuditLogEntry,
  AuditLogFilters,
  AuditReminderEntry,
  AuditReminderSummary,
  acknowledgeAuditAlert,
  downloadAuditPdf,
  exportAuditLogsCsv,
  getAuditLogs,
  getAuditReminders,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

type Props = {
  token: string;
};

type LoadLogsOptions = {
  filters?: Partial<AuditLogFilters>;
  notify?: boolean;
};

const REMINDER_INTERVAL_MS = 120_000;
const SNOOZE_DURATION_MS = 10 * 60 * 1000;

function AuditLog({ token }: Props) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [limit, setLimit] = useState(50);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState<"" | AuditLogEntry["severity"]>("");
  const [userFilter, setUserFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const [reminders, setReminders] = useState<AuditReminderSummary | null>(null);
  const [reminderLoading, setReminderLoading] = useState(false);
  const [reminderError, setReminderError] = useState<string | null>(null);

  const [selectedReminder, setSelectedReminder] = useState<AuditReminderEntry | null>(null);
  const [ackNote, setAckNote] = useState("");
  const [ackReason, setAckReason] = useState("");
  const [ackError, setAckError] = useState<string | null>(null);
  const [acknowledging, setAcknowledging] = useState(false);

  const [snoozedUntil, setSnoozedUntil] = useState<number | null>(null);

  const { pushToast } = useDashboard();

  const reminderIntervalRef = useRef<number | null>(null);
  const snoozeTimeoutRef = useRef<number | null>(null);
  const snoozedUntilRef = useRef<number | null>(null);
  const reminderSummaryRef = useRef<AuditReminderSummary | null>(null);
  const lastToastRef = useRef<number>(0);

  const moduleOptions = useMemo(
    () => [
      { value: "", label: "Todos" },
      { value: "inventario", label: "Inventario" },
      { value: "ventas", label: "Ventas/POS" },
      { value: "compras", label: "Compras" },
      { value: "configuracion", label: "Configuración" },
      { value: "sincronizacion", label: "Sincronización" },
      { value: "clientes", label: "Clientes" },
      { value: "proveedores", label: "Proveedores" },
      { value: "usuarios", label: "Usuarios/Seguridad" },
      { value: "respaldos", label: "Respaldos" },
      { value: "general", label: "General" },
    ],
    []
  );

  const clearReminderInterval = useCallback(() => {
    if (reminderIntervalRef.current !== null) {
      window.clearInterval(reminderIntervalRef.current);
      reminderIntervalRef.current = null;
    }
  }, []);

  const clearSnoozeTimeout = useCallback(() => {
    if (snoozeTimeoutRef.current !== null) {
      window.clearTimeout(snoozeTimeoutRef.current);
      snoozeTimeoutRef.current = null;
    }
  }, []);

  const buildCurrentFilters = useCallback(
    (overrides: Partial<AuditLogFilters> = {}): AuditLogFilters => {
      const filters: AuditLogFilters = {};
      const limitValue = overrides.limit ?? limit;
      if (typeof limitValue === "number" && !Number.isNaN(limitValue)) {
        filters.limit = limitValue;
      }
      const normalizedAction = overrides.action ?? (actionFilter.trim() ? actionFilter.trim() : undefined);
      if (normalizedAction) {
        filters.action = normalizedAction;
      }
      const normalizedEntity = overrides.entity_type ?? (entityFilter.trim() ? entityFilter.trim() : undefined);
      if (normalizedEntity) {
        filters.entity_type = normalizedEntity;
      }
      const normalizedModule = overrides.module ?? (moduleFilter.trim() ? moduleFilter.trim() : undefined);
      if (normalizedModule) {
        filters.module = normalizedModule;
      }
      const overrideUser = overrides.performed_by_id;
      let effectiveUser = overrideUser;
      if (typeof effectiveUser !== "number") {
        const trimmed = userFilter.trim();
        if (trimmed) {
          const parsed = Number(trimmed);
          if (!Number.isNaN(parsed)) {
            effectiveUser = parsed;
          }
        }
      }
      if (typeof effectiveUser === "number" && Number.isFinite(effectiveUser) && effectiveUser > 0) {
        filters.performed_by_id = effectiveUser;
      }
      const normalizedSeverity = overrides.severity ?? (severityFilter || undefined);
      if (normalizedSeverity) {
        filters.severity = normalizedSeverity;
      }
      const fromValue = overrides.date_from ?? (dateFrom || undefined);
      if (fromValue) {
        filters.date_from = fromValue;
      }
      const toValue = overrides.date_to ?? (dateTo || undefined);
      if (toValue) {
        filters.date_to = toValue;
      }
      return filters;
    },
    [actionFilter, dateFrom, dateTo, entityFilter, limit, moduleFilter, severityFilter, userFilter]
  );

  const loadLogs = useCallback(
    async ({ filters: overrides, notify }: LoadLogsOptions = {}) => {
      try {
        if (!notify) {
          setLoading(true);
          setError(null);
        }
        const effectiveFilters = buildCurrentFilters(overrides);
        const data = await getAuditLogs(token, effectiveFilters);
        setLogs((previous) => {
          if (notify && previous.length > 0 && data.length > 0) {
            const latest = data[0];
            const previousFirst = previous[0];
            if (latest && previousFirst && latest.id !== previousFirst.id) {
              pushToast({ message: `Nueva acción registrada: ${latest.action}`, variant: "info" });
            }
          }
          return data;
        });
        if (!notify) {
          setError(null);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible consultar la bitácora";
        if (!notify) {
          setError(message);
        }
        pushToast({ message, variant: "error" });
      } finally {
        if (!notify) {
          setLoading(false);
        }
      }
    },
    [buildCurrentFilters, pushToast, token]
  );

  const loadReminders = useCallback(
    async ({ silent = false }: { silent?: boolean } = {}) => {
      try {
        if (!silent) {
          setReminderLoading(true);
          setReminderError(null);
        }
        const data = await getAuditReminders(token);
        const previous = reminderSummaryRef.current;
        reminderSummaryRef.current = data;
        setReminders(data);

        const now = Date.now();
        const isSnoozed = snoozedUntilRef.current !== null && now < snoozedUntilRef.current;
        const hasPending = data.pending_count > 0;
        if (!isSnoozed && hasPending) {
          let hasNewPending = false;
          if (!previous) {
            hasNewPending = true;
          } else {
            const previousPending = new Map(
              previous.persistent
                .filter((entry) => entry.status === "pending")
                .map((entry) => [`${entry.entity_type}:${entry.entity_id}`, entry.last_seen])
            );
            hasNewPending = data.persistent.some((entry) => {
              if (entry.status !== "pending") {
                return false;
              }
              const key = `${entry.entity_type}:${entry.entity_id}`;
              const lastSeen = previousPending.get(key);
              return !lastSeen || lastSeen !== entry.last_seen;
            });
          }

          if (hasNewPending && (!silent || now - lastToastRef.current > 45_000)) {
            const mostRecent = [...data.persistent]
              .filter((entry) => entry.status === "pending")
              .sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime())[0];
            const message = mostRecent
              ? `Alerta pendiente: ${mostRecent.entity_type} #${mostRecent.entity_id} (${new Date(
                  mostRecent.last_seen
                ).toLocaleTimeString("es-MX")})`
              : `Tienes ${data.pending_count} alertas críticas pendientes`;
            pushToast({ message, variant: "warning" });
            lastToastRef.current = now;
          }
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible obtener recordatorios";
        if (!silent) {
          setReminderError(message);
        }
        pushToast({ message, variant: "error" });
      } finally {
        if (!silent) {
          setReminderLoading(false);
        }
      }
    },
    [pushToast, token]
  );

  const startReminderInterval = useCallback(() => {
    if (reminderIntervalRef.current !== null) {
      return;
    }
    reminderIntervalRef.current = window.setInterval(() => {
      void loadReminders({ silent: true });
    }, REMINDER_INTERVAL_MS);
  }, [loadReminders]);

  const requestReason = useCallback(
    (defaultReason: string): string | null => {
      const value = window.prompt("Ingresa el motivo corporativo (X-Reason ≥ 5 caracteres)", defaultReason);
      if (!value) {
        pushToast({ message: "Acción cancelada: se requiere motivo corporativo.", variant: "info" });
        return null;
      }
      const trimmed = value.trim();
      if (trimmed.length < 5) {
        pushToast({ message: "El motivo corporativo debe tener al menos 5 caracteres.", variant: "error" });
        return null;
      }
      return trimmed;
    },
    [pushToast]
  );

  const handleSnooze = useCallback(() => {
    clearReminderInterval();
    const until = Date.now() + SNOOZE_DURATION_MS;
    setSnoozedUntil(until);
    snoozedUntilRef.current = until;
    clearSnoozeTimeout();
    snoozeTimeoutRef.current = window.setTimeout(() => {
      setSnoozedUntil(null);
      snoozedUntilRef.current = null;
      pushToast({ message: "Snooze finalizado, recordatorios reactivados.", variant: "info" });
      startReminderInterval();
      void loadReminders({ silent: true });
    }, SNOOZE_DURATION_MS);
    pushToast({ message: "Recordatorios pausados por 10 minutos.", variant: "info" });
  }, [clearReminderInterval, clearSnoozeTimeout, loadReminders, pushToast, startReminderInterval]);

  const handleResumeReminders = useCallback(() => {
    const wasSnoozed = snoozedUntilRef.current !== null;
    clearSnoozeTimeout();
    setSnoozedUntil(null);
    snoozedUntilRef.current = null;
    startReminderInterval();
    void loadReminders({ silent: false });
    pushToast({
      message: wasSnoozed ? "Recordatorios reanudados." : "Recordatorios activos.",
      variant: "info",
    });
  }, [clearSnoozeTimeout, loadReminders, pushToast, startReminderInterval]);

  const handleFilter = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void loadLogs({ notify: false });
    },
    [loadLogs]
  );

  const handleDownload = useCallback(
    async (type: "csv" | "pdf") => {
      try {
        const reasonDefault = type === "csv" ? "Descarga auditoría" : "Reporte auditoría";
        const reason = requestReason(reasonDefault);
        if (!reason) {
          return;
        }
        setDownloading(true);
        const filters = buildCurrentFilters();
        const blob =
          type === "csv"
            ? await exportAuditLogsCsv(token, filters, reason)
            : await downloadAuditPdf(token, filters, reason);
        const fileName = type === "csv" ? "bitacora_auditoria.csv" : "bitacora_auditoria.pdf";
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        pushToast({ message: `Descarga generada: ${fileName}`, variant: "success" });
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible generar el archivo";
        pushToast({ message, variant: "error" });
      } finally {
        setDownloading(false);
      }
    },
    [buildCurrentFilters, pushToast, requestReason, token]
  );

  const handleSelectReminder = useCallback((entry: AuditReminderEntry) => {
    setSelectedReminder(entry);
    setAckNote(entry.acknowledged_note ?? "");
    setAckReason("");
    setAckError(null);
  }, []);

  const handleCancelAcknowledgement = useCallback(() => {
    setSelectedReminder(null);
    setAckNote("");
    setAckReason("");
    setAckError(null);
  }, []);

  const handleAcknowledge = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedReminder) {
        return;
      }
      const trimmedReason = ackReason.trim();
      if (trimmedReason.length < 5) {
        setAckError("El motivo corporativo debe tener al menos 5 caracteres.");
        return;
      }
      const note = ackNote.trim();
      setAckError(null);
      try {
        setAcknowledging(true);
        const payload: Parameters<typeof acknowledgeAuditAlert>[1] = {
          entity_type: selectedReminder.entity_type,
          entity_id: selectedReminder.entity_id,
        };

        if (note) {
          payload.note = note;
        }

        await acknowledgeAuditAlert(token, payload, trimmedReason);
        pushToast({
          message: `Acuse registrado para ${selectedReminder.entity_type} #${selectedReminder.entity_id}.`,
          variant: "success",
        });
        setSelectedReminder(null);
        setAckNote("");
        setAckReason("");
        await loadReminders({ silent: false });
        await loadLogs({ notify: false });
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible registrar el acuse";
        setAckError(message);
        pushToast({ message, variant: "error" });
      } finally {
        setAcknowledging(false);
      }
    },
    [ackNote, ackReason, loadLogs, loadReminders, pushToast, selectedReminder, token]
  );

  const severitySummary = useMemo(() => {
    return logs.reduce(
      (acc, log) => {
        if (log.severity === "critical") {
          acc.critical += 1;
        } else if (log.severity === "warning") {
          acc.warning += 1;
        }
        return acc;
      },
      { critical: 0, warning: 0 }
    );
  }, [logs]);

  const highlightedLogs = useMemo(
    () => logs.filter((log) => log.severity !== "info").slice(0, 3),
    [logs]
  );

  const pendingReminders = useMemo(() => {
    if (!reminders) {
      return [] as AuditReminderEntry[];
    }
    return reminders.persistent
      .filter((entry) => entry.status === "pending")
      .sort((a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime());
  }, [reminders]);

  const acknowledgedReminders = useMemo(() => {
    if (!reminders) {
      return [] as AuditReminderEntry[];
    }
    return reminders.persistent
      .filter((entry) => entry.status === "acknowledged")
      .sort((a, b) => {
        const dateB = b.acknowledged_at ? new Date(b.acknowledged_at).getTime() : 0;
        const dateA = a.acknowledged_at ? new Date(a.acknowledged_at).getTime() : 0;
        return dateB - dateA;
      });
  }, [reminders]);

  const resolveSeverityClass = (severity: AuditLogEntry["severity"]) => {
    if (severity === "critical") {
      return "danger";
    }
    if (severity === "warning") {
      return "warning";
    }
    return "neutral";
  };

  const resolveActionIcon = (action: string): string => {
    const normalized = action.toLowerCase();
    if (normalized.includes("login") || normalized.includes("auth")) {
      return "🔒";
    }
    if (normalized.includes("backup")) {
      return "🧾";
    }
    if (normalized.includes("sync")) {
      return "🔄";
    }
    return "⚙️";
  };

  const formatRelativeFromNow = (isoString: string): string => {
    const timestamp = new Date(isoString).getTime();
    if (Number.isNaN(timestamp)) {
      return "fecha desconocida";
    }
    const diffMs = timestamp - Date.now();
    const diffMinutes = Math.round(diffMs / 60000);
    const formatter = new Intl.RelativeTimeFormat("es-MX", { numeric: "auto" });
    if (Math.abs(diffMinutes) < 60) {
      return formatter.format(diffMinutes, "minute");
    }
    const diffHours = Math.round(diffMinutes / 60);
    if (Math.abs(diffHours) < 24) {
      return formatter.format(diffHours, "hour");
    }
    const diffDays = Math.round(diffHours / 24);
    return formatter.format(diffDays, "day");
  };

  useEffect(() => {
    void loadLogs({ notify: false });
    void loadReminders({ silent: false });
  }, [loadLogs, loadReminders]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadLogs({ notify: true });
    }, 45_000);
    return () => window.clearInterval(interval);
  }, [loadLogs]);

  useEffect(() => {
    startReminderInterval();
    return () => {
      clearReminderInterval();
      clearSnoozeTimeout();
    };
  }, [clearReminderInterval, clearSnoozeTimeout, startReminderInterval]);

  useEffect(() => {
    snoozedUntilRef.current = snoozedUntil;
  }, [snoozedUntil]);

  return (
    <section className="card audit-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Bitácora de auditoría</h2>
        <p className="card-subtitle">Revisión en tiempo real de acciones sensibles registradas por el backend.</p>
      </header>
      <form className="audit-filters" onSubmit={handleFilter}>
        <label>
          <span>Acción</span>
          <input
            type="text"
            placeholder="Ej. sale_registered"
            value={actionFilter}
            onChange={(event) => setActionFilter(event.target.value)}
          />
        </label>
        <label>
          <span>Entidad</span>
          <input
            type="text"
            placeholder="Ej. sale"
            value={entityFilter}
            onChange={(event) => setEntityFilter(event.target.value)}
          />
        </label>
        <label>
          <span>Módulo</span>
          <select value={moduleFilter} onChange={(event) => setModuleFilter(event.target.value)}>
            {moduleOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Límite</span>
          <input
            type="number"
            min={10}
            max={500}
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />
        </label>
        <label>
          <span>Severidad</span>
          <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value as AuditLogEntry["severity"] | "")}> 
            <option value="">Todas</option>
            <option value="critical">Crítica</option>
            <option value="warning">Preventiva</option>
            <option value="info">Informativa</option>
          </select>
        </label>
        <label>
          <span>ID usuario</span>
          <input
            type="number"
            min={1}
            value={userFilter}
            onChange={(event) => setUserFilter(event.target.value)}
          />
        </label>
        <label>
          <span>Desde</span>
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </label>
        <label>
          <span>Hasta</span>
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </label>
        <button className="btn btn--primary" type="submit" disabled={loading}>
          Aplicar filtros
        </button>
      </form>
      <div className="audit-actions">
        <button
          className="btn btn--secondary"
          type="button"
          disabled={downloading}
          onClick={() => void handleDownload("csv")}
        >
          Descargar CSV
        </button>
        <button
          className="btn btn--ghost"
          type="button"
          disabled={downloading}
          onClick={() => void handleDownload("pdf")}
        >
          Descargar PDF
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      {loading ? (
        <p>Cargando eventos...</p>
      ) : (
        <div className="audit-log-table">
          {severitySummary.critical > 0 ? (
            <div className="alert error">
              🔐 Se detectaron {severitySummary.critical} eventos críticos. {" "}
              {highlightedLogs.length > 0
                ? highlightedLogs
                    .map((log) => `${log.action} (${new Date(log.created_at).toLocaleString()})`)
                    .join(" · ")
                : "Revisa los registros recientes para más detalles."}
            </div>
          ) : severitySummary.warning > 0 ? (
            <div className="alert warning">
              ⚠️ {severitySummary.warning} acciones preventivas registradas en este rango. Supervisa los accesos sensibles.
            </div>
          ) : (
            <span className="pill success">Sin alertas de seguridad en la ventana seleccionada</span>
          )}
          <table>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Acción</th>
                <th>Entidad</th>
                <th>Módulo</th>
                <th>Usuario</th>
                <th>Detalle</th>
                <th>Severidad</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr
                  key={log.id}
                  className={
                    log.severity === "critical"
                      ? "critical-row"
                      : log.severity === "warning"
                      ? "warning-row"
                      : undefined
                  }
                >
                  <td>{new Date(log.created_at).toLocaleString()}</td>
                  <td>
                    <span aria-hidden="true" role="img" style={{ marginRight: "0.5rem" }}>
                      {resolveActionIcon(log.action)}
                    </span>
                    <span>{log.action}</span>
                  </td>
                  <td>{log.entity_type} #{log.entity_id}</td>
                  <td>{log.module ?? "general"}</td>
                  <td>{log.performed_by_id ?? "-"}</td>
                  <td>{log.details ?? "-"}</td>
                  <td>
                    <span className={`pill ${resolveSeverityClass(log.severity)}`}>
                      {log.severity_label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="audit-reminders">
        <header className="reminder-header">
          <h3>Recordatorios de alertas críticas</h3>
          <p className="muted-text">
            Umbral corporativo: {reminders?.threshold_minutes ?? 0} minutos · Mínimo de repeticiones: {reminders?.min_occurrences ?? 0}
          </p>
        </header>
        <div className="reminder-actions">
          <span className="pill danger">Pendientes: {reminders?.pending_count ?? 0}</span>
          <span className="pill info">Atendidas: {reminders?.acknowledged_count ?? 0}</span>
          {snoozedUntil ? (
            <button className="btn btn--secondary" type="button" onClick={handleResumeReminders}>
              Reanudar recordatorios
            </button>
          ) : (
            <button className="btn btn--ghost" type="button" onClick={handleSnooze}>
              Posponer 10 minutos
            </button>
          )}
        </div>
        {snoozedUntil ? (
          <p className="muted-text">
            Recordatorios pausados hasta {new Date(snoozedUntil).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}.
          </p>
        ) : null}
        {reminderError && <p className="error-text">{reminderError}</p>}
        {reminderLoading && <p>Cargando recordatorios...</p>}
        {!reminderLoading && reminders && pendingReminders.length === 0 ? (
          <p className="muted-text">Sin alertas críticas pendientes en este momento.</p>
        ) : null}
        {pendingReminders.length > 0 ? (
          <table className="reminder-table">
            <thead>
              <tr>
                <th>Entidad</th>
                <th>Última acción</th>
                <th>Repeticiones</th>
                <th>Visto por última vez</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {pendingReminders.map((reminder) => (
                <tr key={`${reminder.entity_type}-${reminder.entity_id}`}>
                  <td>
                    {reminder.entity_type} #{reminder.entity_id}
                  </td>
                  <td>{reminder.latest_action}</td>
                  <td>{reminder.occurrences}</td>
                  <td>{new Date(reminder.last_seen).toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={() => handleSelectReminder(reminder)}
                    >
                      Registrar acuse
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {acknowledgedReminders.length > 0 ? (
          <details className="acknowledged-reminders" open>
            <summary>Últimos acuses registrados</summary>
            <ul>
              {acknowledgedReminders.slice(0, 5).map((reminder) => (
                <li key={`ack-${reminder.entity_type}-${reminder.entity_id}`}>
                  {reminder.entity_type} #{reminder.entity_id} · {reminder.acknowledged_by_name ?? "Usuario corporativo"} · {reminder.acknowledged_at ? formatRelativeFromNow(reminder.acknowledged_at) : "sin fecha"}
                  {reminder.acknowledged_note ? ` — ${reminder.acknowledged_note}` : ""}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </div>

      {selectedReminder ? (
        <form className="acknowledgement-form" onSubmit={handleAcknowledge}>
          <h4>
            Registrar acuse para {selectedReminder.entity_type} #{selectedReminder.entity_id}
          </h4>
          <label>
            <span>Nota corporativa</span>
            <textarea
              value={ackNote}
              onChange={(event) => setAckNote(event.target.value)}
              placeholder="Describe la acción correctiva o el contexto adicional"
            />
          </label>
          <label>
            <span>Motivo corporativo (X-Reason)</span>
            <input
              type="text"
              value={ackReason}
              onChange={(event) => setAckReason(event.target.value)}
              placeholder="Ej. Revisión manual en sitio"
            />
          </label>
          {ackError && <p className="error-text">{ackError}</p>}
          <div className="acknowledgement-actions">
            <button className="btn btn--primary" type="submit" disabled={acknowledging}>
              {acknowledging ? "Registrando..." : "Guardar acuse"}
            </button>
            <button className="btn btn--ghost" type="button" onClick={handleCancelAcknowledgement}>
              Cancelar
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}

export default AuditLog;
