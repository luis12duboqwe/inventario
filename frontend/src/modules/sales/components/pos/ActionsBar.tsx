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
    <div className="pos-actions-bar">
      <RequirePerm perm={PERMS.POS_HOLD} fallback={null}>
        <button onClick={onHold} className="pos-action-button pos-action-button-default">
          Guardar
        </button>
      </RequirePerm>
      <DisableIfNoPerm perm={PERMS.POS_CHECKOUT}>
        <button onClick={onPay} className="pos-action-button pos-action-button-pay">
          Cobrar
        </button>
      </DisableIfNoPerm>
      <button onClick={onPrint} className="pos-action-button pos-action-button-default">
        Imprimir
      </button>
      <button
        onClick={onSendEmail}
        disabled={!canSend || sendingChannel === "email"}
        aria-busy={sendingChannel === "email"}
        className={`pos-action-button pos-action-button-email ${
          !canSend ? "pos-action-button-disabled" : ""
        }`}
      >
        Enviar correo
      </button>
      <button
        onClick={onSendWhatsapp}
        disabled={!canSend || sendingChannel === "whatsapp"}
        aria-busy={sendingChannel === "whatsapp"}
        className={`pos-action-button pos-action-button-whatsapp ${
          !canSend ? "pos-action-button-disabled" : ""
        }`}
      >
        Enviar WhatsApp
      </button>
      <button onClick={onOffline} className="pos-action-button pos-action-button-default">
        Offline
      </button>
      <button onClick={onCancel} className="pos-action-button pos-action-button-cancel">
        Cancelar
      </button>
    </div>
  );
}
