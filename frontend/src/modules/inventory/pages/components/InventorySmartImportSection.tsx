import { useMemo } from "react";

import Button from "../../../../shared/components/ui/Button";
import Loader from "../../../../components/common/Loader";
import { useInventoryLayout } from "../context/InventoryLayoutContext";

function InventorySmartImportSection() {
  const {
    downloads: { downloadSmartResultCsv, downloadSmartResultPdf },
    smartImport: {
      smartImportFile,
      setSmartImportFile,
      smartImportPreviewState,
      smartImportResult,
      smartImportOverrides,
      smartImportHeaders,
      smartImportLoading,
      smartImportHistory,
      smartImportHistoryLoading,
  refreshSmartImportHistory,
  pendingDevicesLoading,
  refreshPendingDevices,
      smartPreviewDirty,
      smartFileInputRef,
      handleSmartOverrideChange,
      handleSmartPreview,
      handleSmartCommit,
      resetSmartImportContext,
    },
  } = useInventoryLayout();

  const overrideOptions = useMemo(() => {
    if (!smartImportHeaders) {
      return [] as string[];
    }
    return ["", ...smartImportHeaders];
  }, [smartImportHeaders]);

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <h2>Importar desde Excel (inteligente)</h2>
          <p className="card-subtitle">
            Analiza cualquier archivo Excel o CSV, detecta columnas clave y completa el inventario aunque falten campos.
          </p>
        </div>
      </header>
      <label className="file-input">
        <span>Archivo Excel o CSV</span>
        <input
          ref={smartFileInputRef}
          type="file"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.csv,text/csv"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            setSmartImportFile(file);
            resetSmartImportContext();
          }}
        />
        <small className="muted-text">
          {smartImportFile
            ? `Seleccionado: ${smartImportFile.name}`
            : "Soporta encabezados libres como tienda, modelo, IMEI, precio, cantidad, estado o ubicación."}
        </small>
      </label>
      <div className="smart-import__actions">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => {
            void handleSmartPreview();
          }}
          disabled={!smartImportFile || smartImportLoading}
        >
          {smartImportLoading ? "Analizando…" : "Analizar estructura"}
        </Button>
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={() => {
            void handleSmartCommit();
          }}
          disabled={smartImportLoading || !smartImportFile || smartPreviewDirty || (!smartImportPreviewState && !smartImportResult)}
        >
          {smartImportLoading ? "Procesando…" : "Importar desde Excel (inteligente)"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            void refreshSmartImportHistory();
          }}
          disabled={smartImportHistoryLoading}
        >
          {smartImportHistoryLoading ? "Actualizando historial…" : "Actualizar"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            void refreshPendingDevices();
          }}
          disabled={pendingDevicesLoading}
        >
          {pendingDevicesLoading ? "Actualizando pendientes…" : "Actualizar pendientes"}
        </Button>
      </div>
      {smartPreviewDirty ? (
        <p className="smart-import__note smart-import__note--warning">Reanaliza el archivo para aplicar las reasignaciones de columnas.</p>
      ) : null}
  {smartImportLoading ? <Loader label="Procesando importación inteligente…" variant="spinner" /> : null}
      {smartImportPreviewState ? (
        <div className="smart-import__preview">
          <h4>Columnas detectadas</h4>
          <p className="muted-text">
            Registros incompletos estimados: {smartImportPreviewState.registros_incompletos_estimados}
          </p>
          {smartImportPreviewState.columnas_faltantes.length > 0 ? (
            <p className="smart-import__note smart-import__note--warning">
              Columnas faltantes: {smartImportPreviewState.columnas_faltantes.join(", ")}
            </p>
          ) : (
            <p className="smart-import__note smart-import__note--success">Todas las columnas clave fueron identificadas.</p>
          )}
          {smartImportPreviewState.advertencias.length > 0 ? (
            <ul className="smart-import__warnings">
              {smartImportPreviewState.advertencias.map((warning, index) => {
                const [title, ...rest] = warning.split(":");
                const detail = rest.join(":").trim();
                return (
                  <li key={`preview-warning-${index}`}>
                    <span className="smart-import__warning-title">{title}</span>
                    {detail ? (
                      <>
                        <span className="smart-import__warning-separator">·</span>
                        <span className="smart-import__warning-detail">«{detail}»</span>
                      </>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : null}
          <div className="smart-import__table-wrapper">
            <table className="smart-import__table">
              <thead>
                <tr>
                  <th>Campo del sistema</th>
                  <th>Estado</th>
                  <th>Encabezado detectado / reasignación</th>
                  <th>Tipo</th>
                  <th>Ejemplos</th>
                </tr>
              </thead>
              <tbody>
                {smartImportPreviewState.columnas.map((match) => {
                  const currentHeader = smartImportOverrides[match.campo] ?? match.encabezado_origen ?? "";
                  return (
                    <tr key={match.campo}>
                      <td>{match.campo}</td>
                      <td>
                        <span className={`smart-import-status smart-import-status--${match.estado}`}>
                          {match.estado === "ok" ? "Detectada" : match.estado === "pendiente" ? "Parcial" : "Faltante"}
                        </span>
                      </td>
                      <td>
                        <select
                          value={currentHeader}
                          onChange={(event) => handleSmartOverrideChange(match.campo, event.target.value)}
                        >
                          {overrideOptions.map((option) => (
                            <option key={`${match.campo}-${option || "vacío"}`} value={option}>
                              {option || "Selecciona campo"}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>{match.tipo_dato ?? "—"}</td>
                      <td>{match.ejemplos.join(", ") || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {smartImportResult ? (
        <div className="smart-import__result">
          <h4>Resumen de importación</h4>
          <ul className="metrics-list">
            <li>Total procesados: {smartImportResult.total_procesados}</li>
            <li>Nuevos: {smartImportResult.nuevos}</li>
            <li>Actualizados: {smartImportResult.actualizados}</li>
            <li>Registros incompletos: {smartImportResult.registros_incompletos}</li>
          </ul>
          <div className="smart-import__result-actions">
            <Button variant="ghost" size="sm" type="button" onClick={downloadSmartResultCsv}>
              Descargar resumen CSV
            </Button>
            <Button variant="ghost" size="sm" type="button" onClick={downloadSmartResultPdf}>
              Descargar resumen PDF
            </Button>
          </div>
        </div>
      ) : null}
      <div className="smart-import__history">
        <header className="smart-import__history-header">
          <h4>Historial reciente</h4>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              void refreshSmartImportHistory();
            }}
            disabled={smartImportHistoryLoading}
          >
            {smartImportHistoryLoading ? "Actualizando…" : "Actualizar"}
          </Button>
        </header>
        {smartImportHistoryLoading ? (
          <Loader label="Consultando historial…" variant="spinner" />
        ) : smartImportHistory.length === 0 ? (
          <p className="muted-text">No se registran importaciones recientes.</p>
        ) : (
          <ul className="metrics-list">
            {smartImportHistory.map((entry) => (
              <li key={entry.id}>
                <strong>{entry.nombre_archivo}</strong> · {new Date(entry.fecha).toLocaleString("es-MX")} · {entry.total_registros}
                registros
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default InventorySmartImportSection;
