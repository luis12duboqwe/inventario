import { FileDigit, ShieldCheck } from "lucide-react";

import { useDashboard } from "../../dashboard/context/DashboardContext";

export default function OperationsDte(): JSX.Element {
  const { enableDte, enableTwoFactor } = useDashboard();

  if (!enableDte) {
    return (
      <section className="operations-disabled">
        <h2 className="operations-disabled__title">
          <FileDigit aria-hidden="true" size={20} />
          Documentos electrónicos desactivados
        </h2>
        <p className="operations-disabled__text">
          Define <code>SOFTMOBILE_ENABLE_DTE=1</code> junto con
          <code>SOFTMOBILE_ENABLE_PURCHASES_SALES=1</code> para emitir comprobantes electrónicos
          desde el POS y las ventas corporativas.
        </p>
      </section>
    );
  }

  return (
    <section className="operations-panel">
      <header className="operations-panel__header">
        <h2 className="operations-panel__title">
          <FileDigit aria-hidden="true" size={20} />
          Emisión de DTE habilitada
        </h2>
        <p className="operations-panel__description">
          Configura folios, secuencias y numeración fiscal para sincronizar cada documento
          tributario con el backend y la autoridad correspondiente.
        </p>
      </header>
      <article aria-label="Recomendaciones de seguridad para DTE" className="operations-article">
        <h3 className="operations-article__title">
          <ShieldCheck aria-hidden="true" size={18} />
          Buenas prácticas
        </h3>
        <ul className="operations-article__list">
          <li>
            Solicita motivo corporativo <code>X-Reason</code> en cada emisión.
          </li>
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
