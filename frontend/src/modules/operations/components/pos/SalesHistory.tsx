import { FormEvent, useState } from "react";

import type { PosReturnPayload, PosSaleDetailResponse } from "../../../../services/api/pos";

type SalesHistoryProps = {
  loading: boolean;
  saleDetail: PosSaleDetailResponse | null;
  onSearch: (saleId: number, reason: string) => Promise<void>;
  onReturn: (payload: PosReturnPayload, reason: string) => Promise<void>;
};

// [PACK34-UI]
export default function SalesHistory({ loading, saleDetail, onSearch, onReturn }: SalesHistoryProps) {
  const [searchId, setSearchId] = useState<number | "">("");
  const [searchReason, setSearchReason] = useState("Consulta historial POS");
  const [returnForm, setReturnForm] = useState({ imei: "", productId: "", qty: 1, reason: "Devolución POS" });
  const [submittingReturn, setSubmittingReturn] = useState(false);

  const handleSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!searchId || Number(searchId) <= 0) return;
    await onSearch(Number(searchId), searchReason);
  };

  const handleReturn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!saleDetail) return;
    if (!returnForm.imei && !returnForm.productId) return;
    setSubmittingReturn(true);
    try {
      const payload: PosReturnPayload = {
        originalSaleId: saleDetail.sale.id,
        reason: returnForm.reason,
        items: [
          {
            imei: returnForm.imei || undefined,
            productId: returnForm.productId ? Number(returnForm.productId) : undefined,
            qty: returnForm.qty,
          },
        ],
      };
      await onReturn(payload, returnForm.reason);
      setReturnForm({ imei: "", productId: "", qty: 1, reason: "Devolución POS" });
    } finally {
      setSubmittingReturn(false);
    }
  };

  return (
    <section className="card">
      <header className="card__header">
        <h3 className="card__title">Histórico de ventas</h3>
        <p className="card__subtitle">Busca ventas anteriores por folio y genera devoluciones rápidas.</p>
      </header>

      <form className="pos-history-form" onSubmit={handleSearch}>
        <label>
          <span>Folio de venta</span>
          <input
            type="number"
            min={1}
            value={searchId}
            onChange={(event) => setSearchId(event.target.value ? Number(event.target.value) : "")}
            placeholder="Ingresa el ID de la venta"
            required
          />
        </label>
        <label>
          <span>Motivo corporativo</span>
          <input
            type="text"
            minLength={5}
            value={searchReason}
            onChange={(event) => setSearchReason(event.target.value)}
            required
          />
        </label>
        <button type="submit" className="btn btn--ghost" disabled={loading}>
          {loading ? "Buscando…" : "Buscar"}
        </button>
      </form>

      {saleDetail ? (
        <div className="pos-history-detail">
          <div className="pos-history-detail__summary">
            <p>
              <strong>Venta #{saleDetail.sale.id}</strong> — ${saleDetail.sale.total_amount.toFixed(2)} · {new Date(saleDetail.sale.created_at).toLocaleString()}
            </p>
            <p className="muted-text">{saleDetail.sale.notes ?? "Sin notas"}</p>
          </div>
          <ul className="pos-history-detail__items">
            {saleDetail.sale.items.map((item) => (
              <li key={item.id}>
                <span>
                  {item.device?.sku ?? item.device_id} · {item.quantity} uds.
                </span>
                <span>${item.total_line.toFixed(2)}</span>
              </li>
            ))}
          </ul>

          <form className="pos-return-form" onSubmit={handleReturn}>
            <h4>Registrar devolución</h4>
            <label>
              <span>IMEI</span>
              <input
                type="text"
                value={returnForm.imei}
                onChange={(event) => setReturnForm((prev) => ({ ...prev, imei: event.target.value }))}
                placeholder="Opcional si usas ID"
              />
            </label>
            <label>
              <span>ID producto</span>
              <input
                type="number"
                min={1}
                value={returnForm.productId}
                onChange={(event) =>
                  setReturnForm((prev) => ({ ...prev, productId: event.target.value }))
                }
                placeholder="Opcional si usas IMEI"
              />
            </label>
            <label>
              <span>Cantidad</span>
              <input
                type="number"
                min={1}
                value={returnForm.qty}
                onChange={(event) =>
                  setReturnForm((prev) => ({ ...prev, qty: Number(event.target.value) || 1 }))
                }
                required
              />
            </label>
            <label className="pos-return-form__reason">
              <span>Motivo corporativo</span>
              <input
                type="text"
                minLength={5}
                value={returnForm.reason}
                onChange={(event) => setReturnForm((prev) => ({ ...prev, reason: event.target.value }))}
                required
              />
            </label>
            <button type="submit" className="btn btn--secondary" disabled={submittingReturn}>
              {submittingReturn ? "Registrando…" : "Registrar devolución"}
            </button>
          </form>
        </div>
      ) : (
        <p className="muted-text">Busca una venta para consultar detalles y generar devoluciones.</p>
      )}
    </section>
  );
}

