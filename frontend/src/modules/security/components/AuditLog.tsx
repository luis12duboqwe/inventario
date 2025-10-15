import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AuditLogEntry,
  AuditLogFilters,
  AuditReminderEntry,
  AuditReminderSummary,
  AuditAcknowledgementRequest,
  downloadAuditPdf,
  exportAuditLogsCsv,
  getAuditLogs,
  getAuditReminders,
  acknowledgeAuditAlert,
} from "../../../api";
import { useDashboard } from "../../dashboard/context/DashboardContext";

type Props = {
  token: string;
};

function AuditLog({ token }: Props) {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [limit, setLimit] = useState(50);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [reminders, setReminders] = useState<AuditReminderSummary | null>(null);
  const [remindersLoading, setRemindersLoading] = useState(false);
  const [remindersError, setRemindersError] = useState<string | null>(null);
  const [ackNotes, setAckNotes] = useState<Record<string, string>>({});
  const [ackReasons, setAckReasons] = useState<Record<string, string>>({});
  const [ackErrors, setAckErrors] = useState<Record<string, string>>({});
  const [ackSubmitting, setAckSubmitting] = useState<string | null>(null);
  const [snoozedUntil, setSnoozedUntil] = useState<number | null>(null);
  const { pushToast, refreshSummary } = useDashboard();
  const reminderIntervalRef = useRef<number | null>(null);
  const snoozeTimeoutRef = useRef<number | null>(null);
  const snoozedUntilRef = useRef<number | null>(null);
  const lastToastRef = useRef<number>(0);
  const REMINDER_INTERVAL_MS = 120000;
  const SNOOZE_DURATION_MS = 10 * 60 * 1000;

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
    [actionFilter, dateFrom, dateTo, entityFilter, limit, userFilter]
  );

  const loadLogs = useCallback(
    async ({ filters: overrides, notify }: { filters?: Partial<AuditLogFilters>; notify?: boolean } = {}) => {
      try {
        if (!notify) {
          setLoading(true);
          setError(null);
        }
        const effectiveFilters = buildCurrentFilters(overrides);
        const data = await getAuditLogs(token, effectiveFilters);
        setLogs((previous) => {
          if (notify && previous.length > 0 && data.length > 0 && data[0].id !== previous[0].id) {
            pushToast({ message: `Nueva acción registrada: ${data[0].action}`, variant: "info" });
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
    async ({ silent }: { silent?: boolean } = {}) => {
      try {
        if (!silent) {
          setRemindersLoading(true);
          setRemindersError(null);
        }
        const summary = await getAuditReminders(token);
        setReminders(summary);
        if (!silent) {
          setRemindersError(null);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "No fue posible obtener recordatorios";
        if (!silent) {
          setRemindersError(message);
        }
        pushToast({ message, variant: "error" });
      } finally {
        if (!silent) {
          setRemindersLoading(false);
        }
      }
    },
    [pushToast, token]
  );

  useEffect(() => {
    loadLogs({ notify: false });
    loadReminders();
  }, [loadLogs, loadReminders]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadLogs({ notify: true });
    }, 45000);
    return () => window.clearInterval(interval);
  }, [loadLogs]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadReminders({ silent: true });
    }, 60000);
    return () => window.clearInterval(interval);
  }, [loadReminders]);

  useEffect(() => {
    snoozedUntilRef.current = snoozedUntil;
  }, [snoozedUntil]);

  useEffect(() => {
    return () => {
      clearReminderInterval();
      clearSnoozeTimeout();
    };
  }, [clearReminderInterval, clearSnoozeTimeout]);

  const handleFilter = (event: FormEvent) => {
    event.preventDefault();
    loadLogs({ notify: false });
  };

  const handleDownload = async (type: "csv" | "pdf") => {
    try {
      setDownloading(true);
      const filters = buildCurrentFilters();
      const blob =
        type === "csv" ? await exportAuditLogsCsv(token, filters) : await downloadAuditPdf(token, filters);
      const fileName =
        type === "csv" ? "bitacora_auditoria.csv" : "bitacora_auditoria.pdf";
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
  };

  const handleRefreshReminders = useCallback(() => {
    loadReminders();
  }, [loadReminders]);

  const handleSnoozeReminders = useCallback(() => {
    const target = Date.now() + SNOOZE_DURATION_MS;
    setSnoozedUntil(target);
    clearReminderInterval();
    clearSnoozeTimeout();
    snoozeTimeoutRef.current = window.setTimeout(() => {
      setSnoozedUntil(null);
    }, SNOOZE_DURATION_MS);
    lastToastRef.current = Date.now();
    pushToast({ message: "Recordatorios pospuestos por 10 minutos", variant: "info" });
  }, [SNOOZE_DURATION_MS, clearReminderInterval, clearSnoozeTimeout, pushToast]);

  const updateAckField = useCallback(
    (alert: AuditReminderEntry, field: "note" | "reason", value: string) => {
      const key = `${alert.entity_type}#${alert.entity_id}`;
      setAckErrors((prev) => {
        if (!prev[key]) {
          return prev;
        }
        const { [key]: _removed, ...rest } = prev;
        return rest;
      });
      if (field === "note") {
        setAckNotes((prev) => ({ ...prev, [key]: value }));
      } else {
        setAckReasons((prev) => ({ ...prev, [key]: value }));
      }
    },
    []
  );

  const handleAcknowledgeAlert = useCallback(
    async (alert: AuditReminderEntry) => {
      const key = `${alert.entity_type}#${alert.entity_id}`;
      const reason = (ackReasons[key] ?? "Atencion critica manual").trim();
      if (reason.length < 5) {
        pushToast({ message: "El motivo corporativo debe tener al menos 5 caracteres.", variant: "error" });
        return;
      }
      const note = ackNotes[key]?.trim();
      setAckSubmitting(key);
      try {
        const payload: AuditAcknowledgementRequest = {
          entity_type: alert.entity_type,
          entity_id: alert.entity_id,
          note: note || undefined,
        };
        await acknowledgeAuditAlert(token, payload, reason);
        pushToast({
          message: `Se registró la atención de ${alert.entity_type} #${alert.entity_id}.`,
          variant: "success",
        });
        setAckErrors((prev) => {
          if (!prev[key]) {
            return prev;
          }
          const { [key]: _ignored, ...rest } = prev;
          return rest;
        });
        await Promise.all([loadReminders(), refreshSummary()]);
      } catch (err) {
        let message =
          err instanceof Error ? err.message : "No fue posible registrar la atención de la alerta";
        let variant: "error" | "warning" | "info" = "error";
        const normalized = message.toLowerCase();
        if (normalized.includes("ya fue atendida")) {
          message = "Esta alerta ya cuenta con un acuse posterior al último evento crítico.";
          variant = "info";
        } else if (normalized.includes("no existen alertas críticas")) {
          message = "No hay alertas críticas registradas para esta entidad.";
          variant = "warning";
        }
        setAckErrors((prev) => ({ ...prev, [key]: message }));
        pushToast({ message, variant });
      } finally {
        setAckSubmitting(null);
      }
    },
    [ackNotes, ackReasons, loadReminders, pushToast, refreshSummary, token]
  );

  const persistentAlerts = useMemo<AuditReminderEntry[]>(() => {
    const items = [...(reminders?.persistent ?? [])];
    items.sort((a, b) => {
      if (a.status !== b.status) {
        return a.status === "pending" ? -1 : 1;
      }
      return new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime();
    });
    return items;
  }, [reminders]);

  const pendingAlertsCount = reminders?.pending ?? persistentAlerts.filter((alert) => alert.status === "pending").length;
  const acknowledgedAlertsCount = reminders?.acknowledged_total ?? persistentAlerts.filter((alert) => alert.status === "acknowledged").length;
  const hasPersistentAlerts = persistentAlerts.length > 0;
  const hasPendingAlerts = pendingAlertsCount > 0;
  const reminderThresholdMinutes = reminders?.threshold_minutes ?? 15;
  const reminderMinOccurrences = reminders?.min_occurrences ?? 1;

  useEffect(() => {
    if (!reminders) {
      return;
    }
    const keys = reminders.persistent.map((alert) => `${alert.entity_type}#${alert.entity_id}`);
    setAckNotes((prev) => {
      const next: Record<string, string> = {};
      for (const key of keys) {
        if (prev[key]) {
          next[key] = prev[key];
        }
      }
      return next;
    });
    setAckReasons((prev) => {
      const next: Record<string, string> = {};
      for (const key of keys) {
        next[key] = prev[key] ?? "Atencion critica manual";
      }
      return next;
    });
    setAckErrors((prev) => {
      const next: Record<string, string> = {};
      for (const key of keys) {
        if (prev[key]) {
          next[key] = prev[key];
        }
      }
      return next;
    });
  }, [reminders]);

  useEffect(() => {
    if (!hasPendingAlerts) {
      clearReminderInterval();
      clearSnoozeTimeout();
      lastToastRef.current = 0;
      return;
    }

    const now = Date.now();
    const snoozedUntilValue = snoozedUntilRef.current;
    if (typeof snoozedUntilValue === "number" && now < snoozedUntilValue) {
      clearReminderInterval();
      clearSnoozeTimeout();
      const delay = Math.max(snoozedUntilValue - now + 500, 0);
      snoozeTimeoutRef.current = window.setTimeout(() => {
        setSnoozedUntil(null);
      }, delay);
      return;
    }

    if (now - lastToastRef.current > REMINDER_INTERVAL_MS / 2) {
      pushToast({
        message: `🔐 ${pendingAlertsCount} alertas críticas requieren atención inmediata en Seguridad`,
        variant: "warning",
      });
      lastToastRef.current = now;
    }

    clearReminderInterval();
    reminderIntervalRef.current = window.setInterval(() => {
      const tickNow = Date.now();
      if (snoozedUntilRef.current && tickNow < snoozedUntilRef.current) {
        return;
      }
      lastToastRef.current = tickNow;
      if (pendingAlertsCount > 0) {
        pushToast({
          message: `🔐 Permanecen ${pendingAlertsCount} alertas críticas pendientes. Prioriza la revisión.`,
          variant: "warning",
        });
      }
    }, REMINDER_INTERVAL_MS);

    return () => {
      clearReminderInterval();
    };
  }, [
    REMINDER_INTERVAL_MS,
    clearReminderInterval,
    clearSnoozeTimeout,
    hasPendingAlerts,
    pendingAlertsCount,
    pushToast,
    setSnoozedUntil,
  ]);

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
          onClick={() => handleDownload("csv")}
        >
          Descargar CSV
        </button>
        <button
          className="btn btn--ghost"
          type="button"
          disabled={downloading}
          onClick={() => handleDownload("pdf")}
        >
          Descargar PDF
        </button>
      </div>
      <div className="audit-reminders">
        {remindersLoading && <p className="muted-text">Calculando recordatorios…</p>}
        {remindersError && <p className="error-text">{remindersError}</p>}
        {hasPersistentAlerts ? (
          <aside className="reminder-card">
            <header className="reminder-header">
              <h3>Alertas críticas persistentes</h3>
              <p className="reminder-meta">
                {pendingAlertsCount} incidente{pendingAlertsCount === 1 ? "" : "s"} con más de {reminderThresholdMinutes} minutos sin mitigación (mínimo {reminderMinOccurrences} evento{reminderMinOccurrences === 1 ? "" : "s"}){acknowledgedAlertsCount > 0 ? ` · ${acknowledgedAlertsCount} atendi${acknowledgedAlertsCount === 1 ? "da" : "das"} recientemente` : ""}.
              </p>
            </header>
            <ul className="reminder-list">
              {persistentAlerts.map((alert) => {
                const key = `${alert.entity_type}#${alert.entity_id}`;
                const effectiveReason = ackReasons[key] ?? "Atencion critica manual";
                const ackMoment = alert.acknowledged_at ?? alert.last_seen;
                return (
                  <li
                    key={`${alert.entity_type}-${alert.entity_id}`}
                    className={`reminder-entry ${alert.status === "acknowledged" ? "reminder-entry--ack" : ""}`}
                  >
                    <div className="reminder-entry__info">
                      <span className="reminder-entry__badge">{alert.entity_type}</span>
                      <p className="reminder-entry__action">{alert.latest_action}</p>
                      <span className="reminder-entry__meta">
                        Último evento {formatRelativeFromNow(alert.last_seen)} · #{alert.entity_id}
                      </span>
                      <span
                        className={`reminder-entry__status reminder-entry__status--${alert.status}`}
                      >
                        {alert.status === "acknowledged"
                          ? `Atendida ${formatRelativeFromNow(ackMoment)}${alert.acknowledged_by_name ? ` · ${alert.acknowledged_by_name}` : ""}`
                          : `Pendiente desde ${formatRelativeFromNow(alert.first_seen)}`}
                      </span>
                      {alert.status === "acknowledged" && alert.acknowledged_note && (
                        <p className="reminder-entry__note">“{alert.acknowledged_note}”</p>
                      )}
                    </div>
                    <div className="reminder-entry__stats">
                      <span className="reminder-entry__count">{alert.occurrences}</span>
                      <span className="reminder-entry__label">eventos</span>
                    </div>
                    <div className="reminder-entry__actions">
                      {alert.status === "pending" ? (
                        <form
                          className="reminder-entry__form"
                          onSubmit={(event) => {
                            event.preventDefault();
                            void handleAcknowledgeAlert(alert);
                          }}
                        >
                          <label>
                            <span>Nota interna</span>
                            <textarea
                              rows={2}
                              placeholder="Describe la mitigación aplicada"
                              value={ackNotes[key] ?? ""}
                              onChange={(event) => updateAckField(alert, "note", event.target.value)}
                            />
                          </label>
                          <label>
                            <span>Motivo corporativo</span>
                            <input
                              type="text"
                              minLength={5}
                              required
                              value={effectiveReason}
                              onChange={(event) => updateAckField(alert, "reason", event.target.value)}
                            />
                          </label>
                      <button className="btn btn--secondary" type="submit" disabled={ackSubmitting === key}>
                        {ackSubmitting === key ? "Registrando…" : "Registrar atención"}
                      </button>
                      {ackErrors[key] && (
                        <p className="reminder-entry__error">{ackErrors[key]}</p>
                      )}
                    </form>
                  ) : (
                    <span className="reminder-entry__ack-label">
                      Confirmada por {alert.acknowledged_by_name ?? "equipo"} · {formatRelativeFromNow(ackMoment)}
                    </span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
            <footer className="reminder-actions">
              <button
                className="btn btn--secondary"
                type="button"
                onClick={handleRefreshReminders}
                disabled={remindersLoading}
              >
                Actualizar recordatorios
              </button>
              <button className="btn btn--ghost" type="button" onClick={handleSnoozeReminders}>
                Posponer 10 min
              </button>
              {snoozedUntil && (
                <span className="reminder-snooze-label">
                  Pausado hasta {" "}
                  {new Date(snoozedUntil).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </footer>
          </aside>
        ) : (
          !remindersLoading && (
            <span className="pill neutral reminder-pill">Sin alertas críticas persistentes detectadas</span>
          )
        )}
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
                    .map(
                      (log) => `${log.action} (${new Date(log.created_at).toLocaleString()})`
                    )
                    .join(" · ")
                : "Revisa los registros recientes para más detalles."}
            </div>
          ) : severitySummary.warning > 0 ? (
            <div className="alert warning">
              ⚠️ {severitySummary.warning} acciones preventivas registradas en este rango. Supervisa los
              accesos sensibles.
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
                  <td>
                    {log.entity_type} #{log.entity_id}
                  </td>
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
    </section>
  );
}

export default AuditLog;
