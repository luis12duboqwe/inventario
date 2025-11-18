import { FormEvent, useMemo, useState } from "react";

import type { Sale, SaleHistorySearchResponse } from "../../../api";
import { searchSalesHistory } from "../../../api";

type Props = {
  token: string;
  limit?: number;
};

type SegmentKey = keyof SaleHistorySearchResponse;

const DEFAULT_LIMIT = 25;

const SEGMENTS: Array<{
  key: SegmentKey;
  title: string;
  description: string;
  empty: string;
}> = [
  {
    key: "by_ticket",
    title: "Coincidencias por ticket",
    description: "Resultados exactos por folio o identificador del comprobante.",
    empty: "No se localizaron folios con el valor proporcionado.",
  },
  {
    key: "by_qr",
    title: "Coincidencias por código QR",
    description: "Escanea el recibo impreso y valida la venta en segundos.",
    empty: "Escanea un QR válido para obtener coincidencias.",
  },
  {
    key: "by_customer",
    title: "Coincidencias por cliente",
    description: "Ventas recientes vinculadas al cliente buscado.",
    empty: "No hay ventas registradas para el cliente indicado.",
  },
  {
    key: "by_date",
    title: "Coincidencias por fecha",
    description: "Ventas emitidas durante el día seleccionado.",
    empty: "No hay ventas registradas en la fecha consultada.",
  },
];

function resolveCustomerLabel(sale: Sale): string | null {
  if (sale.customer_name) return sale.customer_name;
  if (sale.customer && "name" in sale.customer && sale.customer.name) {
    return sale.customer.name;
  }
  return null;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("es-HN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ReturnsSearch({ token, limit = DEFAULT_LIMIT }: Props) {
  const [filters, setFilters] = useState({ ticket: "", date: "", customer: "", qr: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SaleHistorySearchResponse | null>(null);

  const hasFilters = useMemo(() => {
    return Boolean(filters.ticket.trim() || filters.date || filters.customer.trim() || filters.qr.trim());
  }, [filters]);

  const handleChange = (field: keyof typeof filters) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { value } = event.currentTarget;
      setFilters((current) => ({ ...current, [field]: value }));
    };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!hasFilters) {
      setError("Ingresa al menos un criterio para realizar la búsqueda.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const response = await searchSalesHistory(token, {
        ticket: filters.ticket.trim() || undefined,
        date: filters.date || undefined,
        customer: filters.customer.trim() || undefined,
        qr: filters.qr.trim() || undefined,
        limit,
      });
      setResults(response);
    } catch (err) {
      setResults(null);
      setError(err instanceof Error ? err.message : "No fue posible consultar el historial.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFilters({ ticket: "", date: "", customer: "", qr: "" });
    setResults(null);
    setError(null);
  };

  const renderSale = (sale: Sale) => {
    const occurredAt = new Date(sale.created_at);
    const storeLabel = sale.store?.name ?? `Sucursal #${sale.store_id}`;
    const customerLabel = resolveCustomerLabel(sale);
    return (
      <li key={sale.id} className="returns-search__item">
        <div className="returns-search__item-header">
          <strong>Venta #{sale.id}</strong>
          <span>{storeLabel}</span>
        </div>
        <div className="returns-search__item-body">
          <span>{occurredAt.toLocaleString()}</span>
          <span>Total ${formatCurrency(sale.total_amount)}</span>
        </div>
        {customerLabel ? (
          <p className="muted-text">Cliente: {customerLabel}</p>
        ) : null}
        {sale.notes ? <p className="muted-text">Notas: {sale.notes}</p> : null}
      </li>
    );
  };

  return (
    <section className="card">
      <header className="card__header">
        <h3 className="card__title">Búsqueda inteligente de devoluciones</h3>
        <p className="card__subtitle">
          Escanea recibos con QR o busca por ticket, cliente y fecha para localizar la venta original antes de
          registrar la devolución.
        </p>
      </header>

      <form className="returns-search__form" onSubmit={handleSubmit}>
        <div className="returns-search__grid">
          <label>
            <span>Ticket o folio</span>
            <input
              type="text"
              value={filters.ticket}
              onChange={handleChange("ticket")}
              placeholder="Ej. SM-000123"
              autoComplete="off"
            />
          </label>
          <label>
            <span>Fecha de operación</span>
            <input type="date" value={filters.date} onChange={handleChange("date")} />
          </label>
          <label>
            <span>Cliente</span>
            <input
              type="text"
              value={filters.customer}
              onChange={handleChange("customer")}
              placeholder="Nombre o razón social"
              autoComplete="off"
            />
          </label>
        </div>

        <label className="returns-search__qr">
          <span>Escaneo de recibo (QR)</span>
          <textarea
            rows={3}
            value={filters.qr}
            onChange={handleChange("qr")}
            placeholder="Escanea o pega el código QR impreso en el ticket."
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <div className="returns-search__actions">
          <button type="submit" className="btn btn--secondary" disabled={loading}>
            {loading ? "Buscando…" : "Buscar historial"}
          </button>
          <button type="button" className="btn btn--ghost" onClick={handleReset} disabled={loading && !hasFilters}>
            Limpiar
          </button>
        </div>
      </form>

      {results ? (
        <div className="returns-search__results">
          {SEGMENTS.map((segment) => {
            const items = results[segment.key];
            return (
              <article key={segment.key} className="returns-search__segment">
                <header>
                  <h4>{segment.title}</h4>
                  <p className="muted-text">{segment.description}</p>
                </header>
                {items.length ? (
                  <ul className="returns-search__list">
                    {items.map((sale) => renderSale(sale))}
                  </ul>
                ) : (
                  <p className="muted-text">{segment.empty}</p>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <p className="muted-text">
          Ingresa criterios y presiona «Buscar historial» para obtener coincidencias de ventas recientes.
        </p>
      )}
    </section>
  );
}
