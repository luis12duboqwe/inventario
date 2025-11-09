import React from "react";
// [PACK26-POS-PERMS-START]
import { PERMS, RequirePerm, DisableIfNoPerm } from "../../../../auth/useAuthz";
// [PACK26-POS-PERMS-END]

type Props = {
  onHold?: () => void;
  onPay?: () => void;
  onCancel?: () => void;
  onPrint?: () => void;
  onOffline?: () => void;
  onSendEmail?: () => void;
  onSendWhatsapp?: () => void;
  canSend?: boolean;
  sendingChannel?: "email" | "whatsapp" | null;
};

export default function ActionsBar({
  onHold,
  onPay,
  onCancel,
  onPrint,
  onOffline,
  onSendEmail,
  onSendWhatsapp,
  canSend = false,
  sendingChannel = null,
}: Props) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
        gap: 8,
      }}
    >
      <RequirePerm perm={PERMS.POS_HOLD} fallback={null}>
        <button onClick={onHold} style={{ padding: "10px 12px", borderRadius: 10 }}>
          Guardar
        </button>
      </RequirePerm>
      <DisableIfNoPerm perm={PERMS.POS_CHECKOUT}>
        <button
          onClick={onPay}
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            background: "#22c55e",
            color: "#0b1220",
            border: 0,
          }}
        >
          Cobrar
        </button>
      </DisableIfNoPerm>
      <button onClick={onPrint} style={{ padding: "10px 12px", borderRadius: 10 }}>
        Imprimir
      </button>
      <button
        onClick={onSendEmail}
        disabled={!canSend || sendingChannel === "email"}
        aria-busy={sendingChannel === "email"}
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          background: "#1d4ed8",
          color: "#f8fafc",
          border: 0,
          opacity: !canSend ? 0.5 : 1,
        }}
      >
        Enviar correo
      </button>
      <button
        onClick={onSendWhatsapp}
        disabled={!canSend || sendingChannel === "whatsapp"}
        aria-busy={sendingChannel === "whatsapp"}
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          background: "#10b981",
          color: "#0b1220",
          border: 0,
          opacity: !canSend ? 0.5 : 1,
        }}
      >
        Enviar WhatsApp
      </button>
      <button onClick={onOffline} style={{ padding: "10px 12px", borderRadius: 10 }}>
        Offline
      </button>
      <button
        onClick={onCancel}
        style={{
          padding: "10px 12px",
          borderRadius: 10,
          background: "#b91c1c",
          color: "#fff",
          border: 0,
        }}
      >
        Cancelar
      </button>
    </div>
  );
}
