import type { CustomerSegmentDefinition } from "../../../../types/customers";

type CustomersSegmentExportsProps = {
  segments: CustomerSegmentDefinition[];
  exportingKey: string | null;
  onExport: (segment: CustomerSegmentDefinition) => void;
};

const CustomersSegmentExports = ({
  segments,
  exportingKey,
  onExport,
}: CustomersSegmentExportsProps) => {
  if (!segments.length) {
    return null;
  }

  return (
    <section
      className="customers-segments-bar"
      aria-label="Exportaciones rápidas por segmento"
    >
      <header className="customers-segments-bar__header">
        <h4>Segmentos rápidos</h4>
        <p className="muted-text">
          Descarga listas curadas y dispara campañas para Mailchimp o SMS en segundos.
        </p>
      </header>
      <div className="customers-segments-bar__actions">
        {segments.map((segment) => {
          const isExporting = exportingKey === segment.key;
          return (
            <button
              key={segment.key}
              type="button"
              className="customers-segments-bar__button"
              onClick={() => onExport(segment)}
              disabled={isExporting}
              aria-busy={isExporting}
            >
              <span className="customers-segments-bar__label">{segment.label}</span>
              <span className="customers-segments-bar__meta">{segment.channel}</span>
              <span className="customers-segments-bar__description">
                {segment.description}
              </span>
              {isExporting ? (
                <span className="customers-segments-bar__status">Generando…</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
};

export default CustomersSegmentExports;
