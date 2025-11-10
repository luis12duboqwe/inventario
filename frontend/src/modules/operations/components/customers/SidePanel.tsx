import { Skeleton } from "@/ui/Skeleton"; // [PACK36-customers]
import { safeArray, safeDate, safeString } from "@/utils/safeValues"; // [PACK36-customers]
import type {
  ContactHistoryEntry,
  Customer,
  CustomerSummary,
} from "../../../../api";
import type { LedgerEntryWithDetails } from "../../../../types/customers";

type Invoice = CustomerSummary["invoices"][number];

type CustomersSidePanelProps = {
  selectedCustomer: Customer | null;
  summary: CustomerSummary | null;
  summaryLoading: boolean;
  summaryError: string | null;
  customerHistory: ContactHistoryEntry[];
  customerNotes: string[];
  recentInvoices: Invoice[];
  ledgerLabels: Record<LedgerEntryWithDetails["entry_type"], string>;
  resolveDetails: (entry: LedgerEntryWithDetails) => LedgerEntryWithDetails;
  formatCurrency: (value: number) => string;
};

const CustomersSidePanel = ({
  selectedCustomer,
  summary,
  summaryLoading,
  summaryError,
  customerHistory,
  customerNotes,
  recentInvoices,
  ledgerLabels,
  resolveDetails,
  formatCurrency,
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
  const segmentCategory = safeString(summary?.customer.segment_category, "—");
  const taxId = safeString(summary?.customer.tax_id, "—");
  const tagsList = Array.isArray(summary?.customer.tags)
    ? summary?.customer.tags.filter((tag) => typeof tag === "string" && tag.trim().length > 0).join(", ") || "Sin etiquetas"
    : "Sin etiquetas";
  const formatDateTime = (value: unknown) => { // [PACK36-customers]
    const parsed = safeDate(value);
    if (!parsed) {
      return "Fecha desconocida";
    }
    return parsed.toLocaleString("es-MX");
  };

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
              <p className="muted-text small">
                Categoría {segmentCategory} · Etiquetas {tagsList} · RTN {taxId}
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
