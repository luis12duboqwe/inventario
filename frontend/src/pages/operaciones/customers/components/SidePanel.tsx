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
  return (
    <div className="panel">
      <div className="panel__header">
        <h3>Perfil financiero</h3>
        <p className="panel__subtitle">
          Consulta ventas, pagos, notas y el saldo disponible para tomar decisiones en el momento.
        </p>
      </div>

      {summaryLoading ? (
        <p className="muted-text">Cargando información del cliente...</p>
      ) : summaryError ? (
        <p className="error-text">{summaryError}</p>
      ) : summary && selectedCustomer ? (
        <div className="customer-summary">
          <div className="summary-header">
            <div>
              <h4>{summary.customer.name}</h4>
              <p className="muted-text">
                Tipo {summary.customer.customer_type} · Estado {summary.customer.status}
              </p>
            </div>
            <div className="summary-financial">
              <div>
                <span className="muted-text">Saldo pendiente</span>
                <strong>${formatCurrency(summary.totals.outstanding_debt)}</strong>
              </div>
              <div>
                <span className="muted-text">Crédito disponible</span>
                <strong>${formatCurrency(summary.totals.available_credit)}</strong>
              </div>
              <div>
                <span className="muted-text">Límite</span>
                <strong>${formatCurrency(summary.totals.credit_limit)}</strong>
              </div>
            </div>
          </div>

          <div className="summary-columns">
            <div>
              <h5>Ventas recientes</h5>
              {summary.sales.length === 0 ? (
                <p className="muted-text">Sin ventas registradas.</p>
              ) : (
                <ul className="summary-list">
                  {summary.sales.slice(0, 5).map((sale) => (
                    <li key={sale.sale_id}>
                      <strong>Venta #{sale.sale_id}</strong>
                      <span className="muted-text">
                        {new Date(sale.created_at).toLocaleString("es-MX")} · {sale.status}
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
              {summary.payments.length === 0 ? (
                <p className="muted-text">Sin pagos recientes.</p>
              ) : (
                <ul className="summary-list">
                  {summary.payments.slice(0, 5).map((payment) => (
                    <li key={payment.id}>
                      <div>
                        <strong>{ledgerLabels[payment.entry_type]}</strong>
                        <span className="muted-text small">
                          {new Date(payment.created_at).toLocaleString("es-MX")}
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
              {recentInvoices.length === 0 ? (
                <p className="muted-text">Sin facturas generadas.</p>
              ) : (
                <ul className="summary-list">
                  {recentInvoices.map((invoice) => (
                    <li key={invoice.invoice_number}>
                      <div>
                        <strong>{invoice.invoice_number}</strong>
                        <span className="muted-text small">
                          {new Date(invoice.created_at).toLocaleString("es-MX")}
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
              {customerNotes.length === 0 && customerHistory.length === 0 ? (
                <p className="muted-text">Sin notas registradas.</p>
              ) : (
                <ul className="notes-stack">
                  {customerNotes.map((note, index) => (
                    <li key={`note-${index}`}>
                      <span className="note-chip">Nota interna</span>
                      <p>{note}</p>
                    </li>
                  ))}
                  {customerHistory.map((entry) => (
                    <li key={`history-${entry.timestamp}`}>
                      <span className="note-chip">
                        Seguimiento · {new Date(entry.timestamp).toLocaleString("es-MX")}
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
            {customerHistory.length === 0 ? (
              <p className="muted-text">Sin interacciones registradas.</p>
            ) : (
              <ul className="history-stack">
                {customerHistory.map((entry) => (
                  <li key={`history-card-${entry.timestamp}`}>
                    <div>
                      <strong>{new Date(entry.timestamp).toLocaleString("es-MX")}</strong>
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
            {summary.ledger.length === 0 ? (
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
                    {summary.ledger.slice(0, 10).map((entry) => {
                      const enriched = resolveDetails(entry);
                      return (
                        <tr key={entry.id}>
                          <td>{new Date(entry.created_at).toLocaleString("es-MX")}</td>
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
