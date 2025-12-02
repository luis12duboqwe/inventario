import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Button from "@components/ui/Button";
import {
  applyApiBaseUrlOverride,
  getCurrentApiBaseUrl,
  resetApiBaseUrlOverride,
} from "@api/http";
import { fetchLanDiscovery, type LanDiscoveryResponse } from "@api/discovery";

type Props = {
  onApplied?: (baseUrl: string) => void;
};

function buildLanLabel(data: LanDiscoveryResponse | undefined): string {
  if (!data) {
    return "Detectando servidor LAN…";
  }
  return `${data.protocol}://${data.host}:${data.port}`;
}

export default function LanDiscoveryAssistant({ onApplied }: Props): JSX.Element {
  const [feedback, setFeedback] = useState<string | null>(null);
  const discoveryQuery = useQuery<LanDiscoveryResponse>({
    queryKey: ["lan-discovery"],
    queryFn: fetchLanDiscovery,
  });

  const [currentBase, setCurrentBase] = useState<string>(() => getCurrentApiBaseUrl());
  const lanLabel = buildLanLabel(discoveryQuery.data);

  const handleApply = () => {
    if (!discoveryQuery.data) {
      return;
    }
    const normalized = applyApiBaseUrlOverride(discoveryQuery.data.api_base_url);
    if (normalized) {
      setFeedback(`Base de API actualizada a ${normalized}`);
      setCurrentBase(normalized);
      onApplied?.(normalized);
    }
  };

  const handleReset = () => {
    const normalized = resetApiBaseUrlOverride();
    setFeedback(`Se restableció la ruta base a ${normalized}`);
    setCurrentBase(normalized);
    onApplied?.(normalized);
  };

  const notes = discoveryQuery.data?.notes ?? [];

  return (
    <section className="card configuration-card" aria-live="polite">
      <header className="configuration-card__header">
        <div>
          <h2>Asistente LAN</h2>
          <p>Detecta el servidor local y aplica la ruta de API para terminales en la misma red.</p>
        </div>
        <div className="lan-assistant__actions">
          <Button
            variant="secondary"
            onClick={() => discoveryQuery.refetch()}
            disabled={discoveryQuery.isFetching}
          >
            {discoveryQuery.isFetching ? "Buscando…" : "Volver a detectar"}
          </Button>
          <Button
            variant="primary"
            disabled={!discoveryQuery.data?.enabled || discoveryQuery.isLoading}
            onClick={handleApply}
          >
            {discoveryQuery.isLoading ? "Cargando…" : "Aplicar en este navegador"}
          </Button>
          <Button variant="ghost" onClick={handleReset}>
            Restablecer
          </Button>
        </div>
      </header>

      <div className="lan-assistant__grid">
        <div className="lan-assistant__panel">
          <div className="lan-assistant__meta">
            <span
              className={
                discoveryQuery.data?.enabled
                  ? "lan-assistant__badge"
                  : "lan-assistant__badge lan-assistant__badge--disabled"
              }
            >
              {discoveryQuery.data?.enabled ? "Descubrimiento activo" : "Descubrimiento desactivado"}
            </span>
            <p className="lan-assistant__label">Servidor LAN detectado</p>
            <div className="lan-assistant__codes">
              <span>{lanLabel}</span>
              <span className="lan-assistant__code">Base API sugerida: {discoveryQuery.data?.api_base_url ?? "…"}</span>
              <span className="lan-assistant__code">Base API actual: {currentBase}</span>
            </div>
          </div>
        </div>

        <div className="lan-assistant__panel">
          <div className="lan-assistant__meta">
            <p className="lan-assistant__label">Base de datos compartida</p>
            <div className="lan-assistant__codes">
              <span>Motor: {discoveryQuery.data?.database.engine ?? "desconocido"}</span>
              <span>Ubicación: {discoveryQuery.data?.database.location ?? "-"}</span>
              <span>
                Modo LAN: {discoveryQuery.data?.database.shared_over_lan ? "Disponible" : "Revisar"}
              </span>
            </div>
            {notes.length > 0 ? (
              <ul className="lan-assistant__list">
                {notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : null}
            {feedback ? <p className="lan-assistant__feedback">{feedback}</p> : null}
            {discoveryQuery.error ? (
              <p className="lan-assistant__feedback">
                No fue posible obtener los datos de la LAN, intenta nuevamente.
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
