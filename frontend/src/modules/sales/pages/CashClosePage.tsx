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
    <div data-testid="cash-close" className="operations-subpage" style={{ display: "grid", gap: 12 }}>
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
              // ...resto de acciones...
            ],
          },
        ]}
      />
      {/* ...resto del componente... */}
    </div>
  );
