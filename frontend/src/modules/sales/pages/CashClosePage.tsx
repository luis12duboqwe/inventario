import React, { useMemo, useState } from "react";
// [PACK26-CASH-PERMS-START]
import { DisableIfNoPerm, PERMS } from "../../../auth/useAuthz";
// [PACK26-CASH-PERMS-END]

type Totals = {
  cash: number;
  card: number;
  transfer: number;
  other: number;
  total: number;
};

const INITIAL_TOTALS: Totals = { cash: 0, card: 0, transfer: 0, other: 0, total: 0 };

export default function CashClosePage() {
  const [theoretical] = useState<Totals>(INITIAL_TOTALS); // TODO(wire)
  const [counted, setCounted] = useState<Totals>(INITIAL_TOTALS);

  const diff = useMemo(() => ({
    cash: counted.cash - theoretical.cash,
    card: counted.card - theoretical.card,
    transfer: counted.transfer - theoretical.transfer,
    other: counted.other - theoretical.other,
    total: counted.total - theoretical.total,
  }), [counted, theoretical]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ fontWeight: 700 }}>Cierre de caja</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700 }}>Teórico</div>
          {(["cash", "card", "transfer", "other", "total"] as const).map((key) => (
            <div key={key} style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
              <span>{key}</span>
              <span>{(theoretical as Record<string, number>)[key]}</span>
            </div>
          ))}
        </div>
        <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12 }}>
          <div style={{ fontWeight: 700 }}>Conteo</div>
          {(["cash", "card", "transfer", "other", "total"] as const).map((key) => (
            <label
              key={key}
              style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}
            >
              <span>{key}</span>
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
        </div>
      </div>
      <div style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12 }}>
        <div style={{ fontWeight: 700 }}>Diferencias</div>
        {Object.entries(diff).map(([key, value]) => (
          <div key={key} style={{ display: "flex", justifyContent: "space-between", marginTop: 6 }}>
            <span>{key}</span>
            <span>{value}</span>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        {/* [PACK26-CASH-PERMS-START] */}
        <DisableIfNoPerm perm={PERMS.CASH_CLOSE}>
          <button
            style={{ padding: "8px 12px", borderRadius: 8 }}
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
  );
}
