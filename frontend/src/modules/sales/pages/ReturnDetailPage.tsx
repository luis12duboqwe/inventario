import React from "react";
// [PACK23-RETURNS-DETAIL-IMPORTS-START]
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { SalesReturns } from "../../../services/sales";
import type { ReturnDoc, ReturnCreate } from "../../../services/sales";
import { linesToTable } from "../utils/adapters";
// [PACK23-RETURNS-DETAIL-IMPORTS-END]
import { ReturnEditor } from "../components/returns";
import { Table } from "../components/common";
// [PACK26-RETURNS-DETAIL-PERMS-START]
import { useAuthz, PERMS, RequirePerm } from "../../../auth/useAuthz";
import { logUI } from "../../../services/audit";
// [PACK26-RETURNS-DETAIL-PERMS-END]
// [PACK27-PRINT-IMPORT-RETURNS-START]
import { openPrintable } from "@/lib/print";
// [PACK27-PRINT-IMPORT-RETURNS-END]
// [PACK25-SKELETON-USE-START]
import { Skeleton } from "@components/ui/Skeleton";
// [PACK25-SKELETON-USE-END]
import { readQueue } from "@/services/offline";
import { flushOffline, safeCreateReturn } from "../utils/offline";

const lineColumns = [
  { key: "name", label: "Producto" },
  { key: "qty", label: "Cantidad", align: "center" as const },
  { key: "price", label: "Precio", align: "right" as const },
  { key: "discount", label: "Descuento", align: "center" as const },
  { key: "total", label: "Total", align: "right" as const },
];

const reasonLabels: Record<ReturnDoc["reason"], string> = {
  DEFECT: "Defecto",
  BUYER_REMORSE: "Remordimiento",
  WARRANTY: "Garantía",
  OTHER: "Otro",
  EXCHANGE: "Cambio",
};

function formatCurrency(value?: number) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("es-HN", { style: "currency", currency: "MXN" }).format(value);
}

function formatDate(value?: string) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export function ReturnDetailPage() {
  const { can, user } = useAuthz();
  const canView = can(PERMS.RETURN_VIEW);
  const canCreate = can(PERMS.RETURN_CREATE);
  // [PACK23-RETURNS-DETAIL-STATE-START]
  const { id } = useParams(); // si no hay id -> modo crear
  const [data, setData] = useState<ReturnDoc | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  // [PACK23-RETURNS-DETAIL-STATE-END]
  const [pendingOffline, setPendingOffline] = useState(0);
  const [flushing, setFlushing] = useState(false);
  const [flushMessage, setFlushMessage] = useState<string | null>(null);
  const [offlineNotice, setOfflineNotice] = useState<string | null>(null);

  // [PACK23-RETURNS-DETAIL-FETCH-START]
  useEffect(() => {
    (async () => {
      if (!id) return;
      if (!canView) {
        setData(null);
        return;
      }
      setLoading(true);
      try {
        setData(await SalesReturns.getReturn(id));
      } finally {
        setLoading(false);
      }
    })();
  }, [id, canView]);
  // [PACK23-RETURNS-DETAIL-FETCH-END]

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setPendingOffline(readQueue().length);
  }, [data]);

  // [PACK23-RETURNS-DETAIL-SAVE-START]
  async function onCreate(payload: ReturnCreate) {
    if (!canCreate) return;
    setSaving(true);
    try {
      const created = await safeCreateReturn(payload); // [PACK37-frontend]
      if (created) {
        setData(created);
        const entityId = created?.id ? String(created.id) : undefined;
        const auditPayload: Parameters<typeof logUI>[0] = {
          ts: Date.now(),
          userId: user?.id ?? null,
          module: "RETURNS",
          action: "create",
        };
        if (entityId) {
          auditPayload.entityId = entityId;
        }
        await logUI(auditPayload); // [PACK37-frontend]
        if (created.printable) {
          openPrintable(created.printable, "nota-devolucion"); // [PACK37-frontend]
        }
        setOfflineNotice(null); // [PACK37-frontend]
      } else {
        setOfflineNotice("Devolución registrada offline. Reintenta sincronizar más tarde."); // [PACK37-frontend]
      }
      if (typeof window !== "undefined") {
        setPendingOffline(readQueue().length); // [PACK37-frontend]
      }
      // TODO: navegar a detalle created.id si tu router lo soporta
    } finally {
      setSaving(false);
    }
  }
  // [PACK23-RETURNS-DETAIL-SAVE-END]

  const handleFlush = useCallback(async () => {
    setFlushing(true);
    try {
      const result = await flushOffline();
      setPendingOffline(result.pending);
      setFlushMessage(`Reintentadas: ${result.flushed}. Pendientes: ${result.pending}.`);
    } catch {
      setFlushMessage("No fue posible sincronizar. Intenta de nuevo más tarde.");
    } finally {
      setFlushing(false);
    }
  }, []);

  const isCreateMode = !id;
  const lineRows = linesToTable(
    (data?.lines || []).map((line) => ({
      productId: line.productId,
      name: line.name ?? String(line.productId),
      qty: line.qty,
      price: line.price,
    })),
  );

  // [PACK26-RETURNS-DETAIL-GUARD-START]
  const unauthorizedView = Boolean(id) && !canView;
  const unauthorizedCreate = !id && !canCreate;
  const unauthorized = unauthorizedView || unauthorizedCreate;
  // [PACK26-RETURNS-DETAIL-GUARD-END]
  const headerSection = useMemo(() => {
    if (!isCreateMode && loading && !data) {
      return <Skeleton lines={6} />;
    }
    return (
      <div className="return-detail-header">
        <h2 className="return-detail-title">Devolución #{data?.number ?? "—"}</h2>
        <span className="return-detail-date">
          {data ? formatDate(data.date) : loading ? "Cargando…" : "—"}
        </span>
      </div>
    );
  }, [data, isCreateMode, loading]);

  return (
    <div className="return-detail-container">
      {unauthorized ? (
        <div>No autorizado</div>
      ) : (
        <>
          {pendingOffline > 0 ? (
            <div className="return-detail-offline-bar">
              <span className="return-detail-offline-text">
                Pendientes offline: {pendingOffline}
              </span>
              <button
                type="button"
                onClick={handleFlush}
                disabled={flushing}
                className="return-detail-offline-btn"
              >
                {flushing ? "Reintentando…" : "Reintentar pendientes"}
              </button>
            </div>
          ) : null}
          {flushMessage ? <div className="return-detail-flush-message">{flushMessage}</div> : null}
          {offlineNotice ? (
            <div className="return-detail-offline-notice">{offlineNotice}</div>
          ) : null}
          {isCreateMode ? (
            <>
              <RequirePerm perm={PERMS.RETURN_CREATE} fallback={<div>No autorizado</div>}>
                <ReturnEditor
                  onSubmit={(payload) => {
                    if (saving) return;
                    const request: ReturnCreate = {
                      reason: payload.reason as ReturnDoc["reason"],
                      lines: payload.lines.map((line) => {
                        const linePayload: ReturnCreate["lines"][number] = {
                          productId: line.id,
                          name: line.name,
                          qty: line.qty,
                          price: line.price,
                        };
                        if (line.imei) {
                          linePayload.imei = line.imei;
                        }
                        if (typeof line.restock === "boolean") {
                          linePayload.restock = line.restock;
                        }
                        return linePayload;
                      }),
                    };
                    if (payload.note) {
                      request.note = payload.note;
                    }
                    if (payload.lines[0]?.ticket) {
                      request.ticketNumber = payload.lines[0]?.ticket;
                    }
                    onCreate(request);
                  }}
                />
              </RequirePerm>
              {data && (
                <div className="return-detail-created-container">
                  <div className="return-detail-created-header">
                    <h2 className="return-detail-title">Devolución #{data.number}</h2>
                    <div className="return-detail-created-actions">
                      <span className="return-detail-date">{formatDate(data.date)}</span>
                      {/* [PACK27-PRINT-BUTTON-START] */}
                      <button
                        className="return-detail-btn-print"
                        onClick={() => openPrintable(data.printable, "documento")}
                        disabled={!data.printable}
                      >
                        Imprimir
                      </button>
                      {/* [PACK27-PRINT-BUTTON-END] */}
                    </div>
                  </div>
                  {headerSection}
                  <div className="return-detail-info">
                    <span>
                      Motivo: <strong>{reasonLabels[data.reason] ?? data.reason}</strong>
                    </span>
                    <span>
                      Crédito: <strong>{formatCurrency(data.totalCredit)}</strong>
                    </span>
                  </div>
                  <Table cols={lineColumns} rows={lineRows} />
                </div>
              )}
            </>
          ) : (
            <div className="return-detail-created-container">
              <div className="return-detail-created-header">
                <h2 className="return-detail-title">Devolución #{data?.number ?? "—"}</h2>
                <div className="return-detail-created-actions">
                  <span className="return-detail-date">
                    {data ? formatDate(data.date) : loading ? "Cargando…" : "—"}
                  </span>
                  {/* [PACK27-PRINT-BUTTON-START] */}
                  <button
                    className="return-detail-btn-print"
                    onClick={() => openPrintable(data?.printable, "documento")}
                    disabled={!data?.printable}
                  >
                    Imprimir
                  </button>
                  {/* [PACK27-PRINT-BUTTON-END] */}
                </div>
              </div>
              {headerSection}
              <div className="return-detail-info">
                <span>
                  Motivo: <strong>{data ? reasonLabels[data.reason] ?? data.reason : "—"}</strong>
                </span>
                <span>
                  Crédito: <strong>{formatCurrency(data?.totalCredit)}</strong>
                </span>
              </div>
              <Table cols={lineColumns} rows={lineRows} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ReturnDetailPage;
