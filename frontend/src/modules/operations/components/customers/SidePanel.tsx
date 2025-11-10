import { Skeleton } from "@/ui/Skeleton"; // [PACK36-customers]
import { safeArray, safeDate, safeString } from "@/utils/safeValues"; // [PACK36-customers]
import type {
  ContactHistoryEntry,
  Customer,
  CustomerAccountsReceivable,
  CustomerSummary,
  CreditScheduleEntry,
} from "../../../../api";
import type { LedgerEntryWithDetails } from "../../../../types/customers";

type Invoice = CustomerSummary["invoices"][number];

type CustomersSidePanelProps = {
  selectedCustomer: Customer | null;
  summary: CustomerSummary | null;
  summaryLoading: boolean;
  summaryError: string | null;
  receivable: CustomerAccountsReceivable | null;
  receivableLoading: boolean;
  receivableError: string | null;
  customerHistory: ContactHistoryEntry[];
  customerNotes: string[];
  recentInvoices: Invoice[];
  ledgerLabels: Record<LedgerEntryWithDetails["entry_type"], string>;
  resolveDetails: (entry: LedgerEntryWithDetails) => LedgerEntryWithDetails;
  formatCurrency: (value: number) => string;
  onDownloadStatement: (customer: Customer) => void;
};

const CustomersSidePanel = ({
  selectedCustomer,
  summary,
  summaryLoading,
  summaryError,
  receivable,
  receivableLoading,
  receivableError,
  customerHistory,
  customerNotes,
  recentInvoices,
  ledgerLabels,
  resolveDetails,
  formatCurrency,
  onDownloadStatement,
}: CustomersSidePanelProps) => {
  const notes = safeArray(customerNotes); // [PACK36-customers]
  const historyEntries = safeArray(customerHistory); // [PACK36-customers]
  const invoices = safeArray(recentInvoices); // [PACK36-customers]
  const summarySales = safeArray(summary?.sales); // [PACK36-customers]
  const summaryPayments = safeArray(summary?.payments); // [PACK36-customers]
  const summaryLedger = safeArray(summary?.ledger); // [PACK36-customers]
  const summaryTotals = summary?.totals ?? { // [PACK36-customers]
    outstanding_debt: 0,
    available_credit: 0,
    credit_limit: 0,
  };
  const receivableData = receivable;
  const receivableBuckets = safeArray(receivableData?.aging); // [PACK36-customers]
  const receivableEntries = safeArray(receivableData?.open_entries); // [PACK36-customers]
  const receivableSchedule = safeArray(receivableData?.credit_schedule); // [PACK36-customers]
  const scheduleStatusLabels: Record<CreditScheduleEntry["status"], string> = {
    pending: "Programado",
    due_soon: "Próximo",
    overdue: "Vencido",
  };
  const scheduleStatusTone: Record<CreditScheduleEntry["status"], string> = {
    pending: "info",
    due_soon: "warning",
    overdue: "danger",
  };
  const receivableStatusLabels: Record<"current" | "overdue", string> = {
    current: "Al día",
    overdue: "Vencido",
  };
  const receivableStatusTone: Record<"current" | "overdue", string> = {
    current: "info",
    overdue: "danger",
  };
  const formatDateTime = (value: unknown) => { // [PACK36-customers]
    const parsed = safeDate(value);
    if (!parsed) {
      return "Fecha desconocida";
    }
    return parsed.toLocaleString("es-MX");
  };
  const formatDateOnly = (value: unknown) => { // [PACK36-customers]
    const parsed = safeDate(value);
    if (!parsed) {
      return "—";
    }
    return parsed.toLocaleDateString("es-MX");
  };
  const resolveReference = (entry: CustomerAccountsReceivable["open_entries"][number]) => { // [PACK36-customers]
    if (entry.reference) {
      return entry.reference;
    }
    if (entry.reference_type && entry.reference_id) {
      return `${entry.reference_type} ${entry.reference_id}`;
    }
    return `Movimiento #${entry.ledger_entry_id}`;
  };
  const handleStatementClick = () => { // [PACK36-customers]
    if (selectedCustomer) {
      onDownloadStatement(selectedCustomer);
    }
  };
  const receivableSummary = receivableData?.summary ?? null; // [PACK36-customers]
  const statementDisabled = !selectedCustomer || receivableLoading || !receivableSummary; // [PACK36-customers]
  const primaryContact = receivableSummary
    ? safeString(
        receivableSummary.contact_email || receivableSummary.contact_phone,
        "—",
      )
    : "—"; // [PACK36-customers]

  return (
    <div className="panel">
      <div className="panel__header">
        <h3>Perfil financiero</h3>
        <p className="panel__subtitle">
          Consulta ventas, pagos, notas y el saldo disponible para tomar decisiones en el momento.
        </p>
      </div>

      {summaryLoading ? (
        <div className="customer-summary__skeleton" role="status" aria-live="polite">
          {/* [PACK36-customers] */}
          <Skeleton lines={4} />
          <div className="summary-columns" aria-hidden>
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={`summary-skeleton-${index}`} className="summary-card">
                <Skeleton lines={index === 3 ? 6 : 4} />
              </div>
            ))}
          </div>
        </div>
      ) : summaryError ? (
        <p className="error-text">{summaryError}</p>
      ) : summary && selectedCustomer ? (
        <div className="customer-summary">
          <div className="summary-header">
            <div>
              <h4>{summary.customer.name ?? "Cliente sin nombre"}</h4>
              <p className="muted-text">
                Tipo {safeString(summary.customer.customer_type, "—")} · Estado {safeString(summary.customer.status, "—")}
              </p>
            </div>
            <div className="summary-financial">
              <div>
                <span className="muted-text">Saldo pendiente</span>
                <strong>${formatCurrency(summaryTotals.outstanding_debt)}</strong>
              </div>
              <div>
                <span className="muted-text">Crédito disponible</span>
                <strong>${formatCurrency(summaryTotals.available_credit)}</strong>
              </div>
              <div>
                <span className="muted-text">Límite</span>
                <strong>${formatCurrency(summaryTotals.credit_limit)}</strong>
              </div>
            </div>
            </div>

            <div className="receivable-section" aria-live="polite">
              <div className="receivable-header">
                <div>
                  <h5>Cuentas por cobrar</h5>
                  <p className="muted-text small">
                    Vigila vencimientos, aging y recordatorios automáticos para este cliente.
                  </p>
                </div>
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={handleStatementClick}
                  disabled={statementDisabled}
                >
                  Descargar estado de cuenta
                </button>
              </div>
              {receivableLoading ? (
                <div className="receivable-skeleton" role="status" aria-live="polite">
                  <Skeleton lines={3} />
                  <Skeleton lines={2} />
                </div>
              ) : receivableError ? (
                <p className="error-text">{receivableError}</p>
              ) : receivableSummary ? (
                <>
                  <div className="receivable-overview">
                    <div>
                      <span className="muted-text small">Saldo por cobrar</span>
                      <strong>${formatCurrency(receivableSummary.total_outstanding)}</strong>
                    </div>
                    <div>
                      <span className="muted-text small">Crédito disponible</span>
                      <strong>${formatCurrency(receivableSummary.available_credit)}</strong>
                      <span className="muted-text small">
                        Límite ${formatCurrency(receivableSummary.credit_limit)}
                      </span>
                    </div>
                    <div>
                      <span className="muted-text small">Próximo vencimiento</span>
                      <strong>{formatDateOnly(receivableSummary.next_due_date)}</strong>
                      <span className="muted-text small">
                        Promedio {Math.round(receivableSummary.average_days_outstanding)} días
                      </span>
                    </div>
                    <div>
                      <span className="muted-text small">Último pago</span>
                      <strong>{formatDateOnly(receivableSummary.last_payment_at)}</strong>
                      <span className="muted-text small">Contacto principal · {primaryContact}</span>
                    </div>
                  </div>

                  <div>
                    <h6>Distribución por antigüedad</h6>
                    {receivableBuckets.length === 0 ? (
                      <p className="muted-text">Sin documentos con saldo pendiente.</p>
                    ) : (
                      <div className="aging-bars">
                        {receivableBuckets.map((bucket) => (
                          <div key={`${bucket.label}-${bucket.days_from}`} className="aging-bar">
                              <div className="aging-bar__header">
                                <strong>{bucket.label}</strong>
                                <span className="muted-text small">{bucket.count} documentos</span>
                              </div>
                            <div
                              className="aging-bar__track"
                              role="presentation"
                              aria-hidden
                            >
                              <div
                                className="aging-bar__fill"
                                style={{ width: `${Math.min(100, Math.max(0, bucket.percentage))}%` }}
                              />
                            </div>
                            <div className="aging-bar__meta">
                              <span className="summary-amount">${formatCurrency(bucket.amount)}</span>
                              <span className="muted-text small">{bucket.percentage.toFixed(0)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h6>Recordatorios programados</h6>
                    {receivableSchedule.length === 0 ? (
                      <p className="muted-text">No hay recordatorios pendientes para este cliente.</p>
                    ) : (
                      <ul className="schedule-list">
                        {receivableSchedule.map((item) => (
                          <li key={`schedule-${item.sequence}`} className={`schedule-item tone-${scheduleStatusTone[item.status]}`}>
                            <div className="schedule-item__header">
                              <span className={`status-pill tone-${scheduleStatusTone[item.status]}`}>
                                {scheduleStatusLabels[item.status]}
                              </span>
                              <strong>{formatDateOnly(item.due_date)}</strong>
                            </div>
                            <div className="schedule-item__body">
                              <span className="summary-amount">${formatCurrency(item.amount)}</span>
                              <span className="muted-text small">
                                {item.reminder ? item.reminder : "Recordatorio automático"}
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div>
                    <h6>Documentos pendientes</h6>
                    {receivableEntries.length === 0 ? (
                      <p className="muted-text">No hay documentos por cobrar en este momento.</p>
                    ) : (
                      <div className="table-wrapper receivable-table">
                        <table>
                          <thead>
                            <tr>
                              <th>Referencia</th>
                              <th>Emitido</th>
                              <th>Estado</th>
                              <th>Días</th>
                              <th>Saldo</th>
                            </tr>
                          </thead>
                          <tbody>
                            {receivableEntries.map((entry) => (
                              <tr key={`receivable-${entry.ledger_entry_id}`}>
                                <td>
                                  <div className="receivable-reference">
                                    <strong>{resolveReference(entry)}</strong>
                                    {entry.note ? (
                                      <span className="muted-text small">{entry.note}</span>
                                    ) : null}
                                  </div>
                                </td>
                                <td>{formatDateOnly(entry.issued_at)}</td>
                                <td>
                                  <span className={`status-pill tone-${receivableStatusTone[entry.status]}`}>
                                    {receivableStatusLabels[entry.status]}
                                  </span>
                                </td>
                                <td>{entry.days_outstanding}</td>
                                <td>${formatCurrency(entry.balance_due)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <p className="muted-text">Selecciona un cliente para ver sus cuentas por cobrar.</p>
              )}
            </div>

          <div className="summary-columns">
            <div>
              <h5>Ventas recientes</h5>
              {summarySales.length === 0 ? (
                <p className="muted-text">Sin ventas registradas.</p>
              ) : (
                <ul className="summary-list">
                  {summarySales.slice(0, 5).map((sale) => (
                    <li key={sale.sale_id}>
                      <strong>Venta #{sale.sale_id}</strong>
                      <span className="muted-text">
                        {formatDateTime(sale.created_at)} · {safeString(sale.status, "—")}
                      </span>
                      <span className="summary-amount">
                        Total ${formatCurrency(sale.total_amount)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h5>Pagos</h5>
              {summaryPayments.length === 0 ? (
                <p className="muted-text">Sin pagos recientes.</p>
              ) : (
                <ul className="summary-list">
                  {summaryPayments.slice(0, 5).map((payment) => (
                    <li key={payment.id}>
                      <div>
                        <strong>{ledgerLabels[payment.entry_type]}</strong>
                        <span className="muted-text small">
                          {formatDateTime(payment.created_at)}
                        </span>
                      </div>
                      <span className="summary-amount">
                        ${formatCurrency(payment.amount)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h5>Facturas emitidas</h5>
              {invoices.length === 0 ? (
                <p className="muted-text">Sin facturas generadas.</p>
              ) : (
                <ul className="summary-list">
                  {invoices.map((invoice) => (
                    <li key={invoice.invoice_number}>
                      <div>
                        <strong>{invoice.invoice_number}</strong>
                        <span className="muted-text small">
                          {formatDateTime(invoice.created_at)}
                          {invoice.store_id ? ` · Sucursal ${invoice.store_id}` : ""}
                        </span>
                      </div>
                      <span className="summary-amount">
                        ${formatCurrency(invoice.total_amount)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h5>Notas y seguimiento</h5>
              {notes.length === 0 && historyEntries.length === 0 ? (
                <p className="muted-text">Sin notas registradas.</p>
              ) : (
                <ul className="notes-stack">
                  {notes.map((note, index) => (
                    <li key={`note-${index}`}>
                      <span className="note-chip">Nota interna</span>
                      <p>{note}</p>
                    </li>
                  ))}
                  {historyEntries.map((entry) => (
                    <li key={`history-${entry.timestamp}`}>
                      <span className="note-chip">
                        Seguimiento · {formatDateTime(entry.timestamp)}
                      </span>
                      <p>{entry.note}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div>
            <h5>Historial de contacto</h5>
            {historyEntries.length === 0 ? (
              <p className="muted-text">Sin interacciones registradas.</p>
            ) : (
              <ul className="history-stack">
                {historyEntries.map((entry) => (
                  <li key={`history-card-${entry.timestamp}`}>
                    <div>
                      <strong>{formatDateTime(entry.timestamp)}</strong>
                      <span className="muted-text small">Bitácora de seguimiento</span>
                    </div>
                    <p>{entry.note}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h5>Bitácora reciente</h5>
            {summaryLedger.length === 0 ? (
              <p className="muted-text">Aún no hay movimientos registrados.</p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Tipo</th>
                      <th>Detalle</th>
                      <th>Monto</th>
                      <th>Saldo posterior</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summaryLedger.slice(0, 10).map((entry) => {
                      const enriched = resolveDetails(entry);
                      return (
                        <tr key={entry.id}>
                          <td>{formatDateTime(entry.created_at)}</td>
                          <td>{ledgerLabels[entry.entry_type]}</td>
                          <td>
                            {entry.note ?? enriched.detailsLabel ?? "—"}
                            {enriched.detailsValue ? (
                              <span className="muted-text"> · {enriched.detailsValue}</span>
                            ) : null}
                            {entry.created_by ? (
                              <span className="muted-text note-meta">· Registrado por {entry.created_by}</span>
                            ) : null}
                          </td>
                          <td>${formatCurrency(entry.amount)}</td>
                          <td>${formatCurrency(entry.balance_after)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        <p className="muted-text">
          Selecciona un cliente en el listado para visualizar su perfil financiero.
        </p>
      )}
    </div>
  );
};

export default CustomersSidePanel;
