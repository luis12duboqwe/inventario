import React, { useMemo, useState } from "react";
// [PACK26-CASH-PERMS-START]
import { DisableIfNoPerm, PERMS } from "../../../auth/useAuthz";
// [PACK26-CASH-PERMS-END]
import FlowAuditCard from "../../../shared/components/FlowAuditCard";

type Totals = {
  cash: number;
  card: number;
  transfer: number;
  other: number;
};

const INITIAL_TOTALS: Totals = { cash: 0, card: 0, transfer: 0, other: 0 };

export function CashClosePage() {
  const [theoretical] = useState<Totals>(INITIAL_TOTALS); // TODO(wire)
  const [counted, setCounted] = useState<Totals>(INITIAL_TOTALS);

  const computedTheoreticalTotal = useMemo(
    () => theoretical.cash + theoretical.card + theoretical.transfer + theoretical.other,
    [theoretical]
  );

  const computedCountedTotal = useMemo(
    () => counted.cash + counted.card + counted.transfer + counted.other,
    [counted]
  );

  const diff = useMemo(
    () => ({
      cash: counted.cash - theoretical.cash,
      card: counted.card - theoretical.card,
      transfer: counted.transfer - theoretical.transfer,
      other: counted.other - theoretical.other,
      total: computedCountedTotal - computedTheoreticalTotal,
    }),
    [counted, computedCountedTotal, computedTheoreticalTotal, theoretical]
  );

  return (
    <div className="operations-subpage" style={{ display: "grid", gap: 12 }}>
      <FlowAuditCard
        title="Cierre de caja auditado"
        subtitle="Reordenamos los pasos para capturar montos y validar diferencias sin romper la grilla"
        flows={[
          {
            id: "conteo",
            title: "Conteo y conciliación",
            summary: "Llena importes por método, verifica el total automático y documenta diferencias.",
            steps: [
              "Confirma que el efectivo inicial esté registrado en el teórico.",
              "Captura montos contados por método; el total se calcula en automático.",
              "Revisa la sección de diferencias antes de cerrar para evitar reprocesos.",
            ],
            actions: [
              {
                id: "ir-conteo",
                label: "Ir al conteo",
                tooltip: "Desplázate al bloque de captura",
                onClick: () =>
                  document.getElementById("cash-close-counted")?.scrollIntoView({ behavior: "smooth" }),
              },
            ],
          },
          {
            id: "arqueo",
            title: "Entrega y comprobante",
            summary: "Valida diferencias y cierra la caja con un solo botón protegido por permisos.",
            steps: [
              "Confirma que las diferencias estén en 0 o documenta el motivo en el recibo.",
              "Descarga el comprobante de cierre y adjúntalo al arqueo diario.",
              "Notifica al responsable de operaciones cuando se detecten ajustes manuales.",
            ],
            actions: [
              {
                id: "ir-cierre",
                label: "Ir a cierre",
                tooltip: "Bajar a la acción de cierre",
                onClick: () =>
                  document.getElementById("cash-close-action")?.scrollIntoView({ behavior: "smooth" }),
              },
            ],
          },
        ]}
      />

      <div className="card" style={{ display: "grid", gap: 12 }}>
        <div className="card-header" style={{ display: "flex", justifyContent: "space-between" }}>
          <div>
            <p className="eyebrow">Caja</p>
            <h3>Conteo rápido</h3>
            <p className="card-subtitle">Calculamos el total mientras capturas importes individuales.</p>
          </div>
          <div className="muted-text" title="Aplica el motivo corporativo al comprobante de cierre">
            Motivo corporativo obligatorio
          </div>
        </div>

        <div className="card" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
          <div>
            <div className="eyebrow">Teórico</div>
            {(["cash", "card", "transfer", "other"] as const).map((key) => (
              <div key={key} style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
                <span>{key}</span>
                <span>{(theoretical as Record<string, number>)[key]}</span>
              </div>
            ))}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontWeight: 700 }}>
              <span>Total</span>
              <span>{computedTheoreticalTotal}</span>
            </div>
          </div>

          <div id="cash-close-counted">
            <div className="eyebrow">Conteo</div>
            {(["cash", "card", "transfer", "other"] as const).map((key) => (
              <label
                key={key}
                style={{ display: "flex", justifyContent: "space-between", marginTop: 6, gap: 8 }}
              >
                <span title="Captura el monto encontrado para este método">{key}</span>
                <input
                  type="number"
                  value={(counted as Record<string, number>)[key] ?? 0}
                  onChange={(event) =>
                    setCounted({
                      ...counted,
                      [key]: Number(event.target.value ?? 0),
                    })
                  }
                  style={{ padding: 6, borderRadius: 8, width: 160, textAlign: "right" }}
                />
              </label>
            ))}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontWeight: 700 }}>
              <span title="Total calculado automáticamente">Total contado</span>
              <span>{computedCountedTotal}</span>
            </div>
          </div>
        </div>

        <div className="card" style={{ display: "grid", gap: 8 }}>
          <div className="eyebrow">Diferencias</div>
          {Object.entries(diff).map(([key, value]) => (
            <div key={key} style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{key}</span>
              <span title="Diferencia entre teórico y conteo">{value}</span>
            </div>
          ))}
          <p className="muted-text">
            Si las diferencias superan el umbral permitido, documenta el motivo antes de cerrar la caja.
          </p>
        </div>

        <div id="cash-close-action" style={{ display: "flex", justifyContent: "flex-end" }}>
          {/* [PACK26-CASH-PERMS-START] */}
          <DisableIfNoPerm perm={PERMS.CASH_CLOSE}>
            <button
              style={{ padding: "8px 12px", borderRadius: 8 }}
              title="Genera el comprobante y guarda el motivo del arqueo"
              onClick={() => {
                // TODO(save+print)
              }}
            >
              Cerrar caja
            </button>
          </DisableIfNoPerm>
          {/* [PACK26-CASH-PERMS-END] */}
        </div>
      </div>
    </div>
  );
}

export default CashClosePage;
