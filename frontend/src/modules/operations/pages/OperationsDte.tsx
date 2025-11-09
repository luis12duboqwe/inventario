import { FileDigit, ShieldCheck } from "lucide-react";

import { useDashboard } from "../../dashboard/context/DashboardContext";

export default function OperationsDte(): JSX.Element {
  const { enableDte, enableTwoFactor } = useDashboard();

  if (!enableDte) {
    return (
      <section style={{ display: "grid", gap: 12 }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
          <FileDigit aria-hidden="true" size={20} />
          Documentos electrónicos desactivados
        </h2>
        <p style={{ margin: 0, color: "#94a3b8" }}>
          Define <code>SOFTMOBILE_ENABLE_DTE=1</code> junto con
          <code>SOFTMOBILE_ENABLE_PURCHASES_SALES=1</code> para emitir comprobantes
          electrónicos desde el POS y las ventas corporativas.
        </p>
      </section>
    );
  }

  return (
    <section style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 8 }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
          <FileDigit aria-hidden="true" size={20} />
          Emisión de DTE habilitada
        </h2>
        <p style={{ margin: 0, color: "#94a3b8" }}>
          Configura folios, secuencias y numeración fiscal para sincronizar cada
          documento tributario con el backend y la autoridad correspondiente.
        </p>
      </header>
      <article
        aria-label="Recomendaciones de seguridad para DTE"
        style={{
          border: "1px solid rgba(148,163,184,0.25)",
          borderRadius: 12,
          padding: 16,
          display: "grid",
          gap: 8,
          background: "rgba(17,24,39,0.65)",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 16, display: "flex", gap: 8, alignItems: "center" }}>
          <ShieldCheck aria-hidden="true" size={18} />
          Buenas prácticas
        </h3>
        <ul style={{ margin: 0, paddingLeft: 18, color: "#cbd5f5" }}>
          <li>Solicita motivo corporativo <code>X-Reason</code> en cada emisión.</li>
          <li>Sincroniza automáticamente las representaciones PDF y XML.</li>
          <li>
            {enableTwoFactor
              ? "2FA corporativo activo para los emisores autorizados."
              : "Se recomienda habilitar SOFTMOBILE_ENABLE_2FA para reforzar el acceso."}
          </li>
        </ul>
      </article>
    </section>
  );
}
