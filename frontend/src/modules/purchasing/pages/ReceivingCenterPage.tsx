import React, { useState } from "react";
import { ReceiveModal } from "../components/receiving";

export default function ReceivingCenterPage() {
  const [open, setOpen] = useState<boolean>(false);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Recepciones</h2>
        <button
          type="button"
          onClick={() => setOpen(true)}
          style={{ padding: "8px 12px", borderRadius: 8 }}
        >
          Nueva recepción
        </button>
      </div>
      {open ? (
        <ReceiveModal
          open={open}
          onClose={() => setOpen(false)}
          onSubmit={() => {
            // TODO(wire)
          }}
        />
      ) : null}
    </div>
  );
}
