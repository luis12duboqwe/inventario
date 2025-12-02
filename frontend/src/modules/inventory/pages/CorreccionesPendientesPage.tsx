import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Button from "@components/ui/Button";
import TextField from "@components/ui/TextField";
import {
  getImportValidationReport,
  getPendingImportValidations,
  markImportValidationCorrected,
  updateDevice,
  type DeviceUpdateInput,
  type ImportValidationDetail,
  type ImportValidationSummary,
} from "@api/inventory";
import { useDashboard } from "../../dashboard/context/DashboardContext";

const DEFAULT_REASON = "Corrección validación importación";

function buildInitialFormState(validation: ImportValidationDetail | null) {
  if (!validation?.device) {
    return { imei: "", serial: "", marca: "", modelo: "", cantidad: "" };
  }
  return {
    imei: validation.device.imei ?? "",
    serial: validation.device.serial ?? "",
    marca: validation.device.marca ?? "",
    modelo: validation.device.modelo ?? "",
    cantidad: "",
  };
}

function CorreccionesPendientesPage() {
  const { token, pushToast } = useDashboard();
  const [summary, setSummary] = useState<ImportValidationSummary | null>(null);
  const [validations, setValidations] = useState<ImportValidationDetail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ImportValidationDetail | null>(null);
  const [formState, setFormState] = useState(buildInitialFormState(null));
  const [reason, setReason] = useState(DEFAULT_REASON);
  const [saving, setSaving] = useState(false);

  const pendingCount = useMemo(() => validations.length, [validations]);

  const refresh = useCallback(async () => {
    if (!token) {
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const [report, pending] = await Promise.all([
        getImportValidationReport(token),
        getPendingImportValidations(token),
      ]);
      setSummary(report);
      setValidations(pending);
      if (pending.length === 0) {
        setSelected(null);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo recuperar la información";
      setError(message);
      pushToast({ message, variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [pushToast, token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    setFormState(buildInitialFormState(selected));
  }, [selected]);

  const handleSelect = useCallback((validation: ImportValidationDetail) => {
    setSelected(validation);
  }, []);

  const handleInputChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFormState((current) => ({ ...current, [name]: value }));
  }, []);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!token || !selected?.device) {
        return;
      }
      const normalizedReason = reason.trim();
      if (normalizedReason.length < 5) {
        setError("Indica un motivo corporativo de al menos 5 caracteres.");
        return;
      }
      const updates: DeviceUpdateInput = {};
      if (formState.imei.trim() !== (selected.device.imei ?? "")) {
        updates.imei = formState.imei.trim() || null;
      }
      if (formState.serial.trim() !== (selected.device.serial ?? "")) {
        updates.serial = formState.serial.trim() || null;
      }
      if (formState.marca.trim() !== (selected.device.marca ?? "")) {
        updates.marca = formState.marca.trim() || null;
      }
      if (formState.modelo.trim() !== (selected.device.modelo ?? "")) {
        updates.modelo = formState.modelo.trim() || null;
      }
      if (formState.cantidad.trim()) {
        const parsed = Number(formState.cantidad);
        if (Number.isNaN(parsed)) {
          setError("La cantidad debe ser un número válido.");
          return;
        }
        updates.quantity = parsed;
      }
      if (Object.keys(updates).length === 0) {
        setError("No hay cambios por aplicar en la ficha seleccionada.");
        return;
      }
      try {
        setSaving(true);
        setError(null);
        await updateDevice(
          token,
          selected.device.store_id,
          selected.device.id,
          updates,
          normalizedReason,
        );
        await markImportValidationCorrected(token, selected.id, normalizedReason);
        pushToast({ message: "Registro corregido", variant: "success" });
        setSelected(null);
        setFormState(buildInitialFormState(null));
        await refresh();
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo aplicar la corrección";
        setError(message);
        pushToast({ message, variant: "error" });
      } finally {
        setSaving(false);
      }
    },
    [formState, pushToast, reason, refresh, selected, token],
  );

  return (
    <div className="section-grid">
      <section className="card wide">
        <header className="card-header">
          <div>
            <h1>Validación avanzada</h1>
            <p className="card-subtitle">
              Revisa los hallazgos posteriores a la importación y aplica correcciones sobre los
              registros pendientes.
            </p>
          </div>
          <div className="card-actions">
            <Button
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => void refresh()}
              disabled={loading}
            >
              Actualizar
            </Button>
            <a
              className="ui-button ui-button--secondary ui-button--sm"
              href="/validacion/exportar?formato=excel"
              target="_blank"
              rel="noopener noreferrer"
            >
              Descargar Excel
            </a>
            <a
              className="ui-button ui-button--ghost ui-button--sm"
              href="/validacion/exportar?formato=pdf"
              target="_blank"
              rel="noopener noreferrer"
            >
              Descargar PDF
            </a>
          </div>
        </header>
        <div className="card-body">
          {summary ? (
            <dl className="summary-grid" aria-label="Resumen de validaciones">
              <div>
                <dt>Registros revisados</dt>
                <dd>{summary.registros_revisados}</dd>
              </div>
              <div>
                <dt>Advertencias activas</dt>
                <dd>{summary.advertencias}</dd>
              </div>
              <div>
                <dt>Errores pendientes</dt>
                <dd>{summary.errores}</dd>
              </div>
              <div>
                <dt>Campos faltantes</dt>
                <dd>
                  {summary.campos_faltantes.length > 0
                    ? summary.campos_faltantes.join(", ")
                    : "Ninguno"}
                </dd>
              </div>
              <div>
                <dt>Tiempo total (s)</dt>
                <dd>{summary.tiempo_total ?? "N/D"}</dd>
              </div>
              <div>
                <dt>Registros pendientes</dt>
                <dd>{pendingCount}</dd>
              </div>
            </dl>
          ) : (
            <p className="muted-text">
              El resumen estará disponible después de la siguiente importación.
            </p>
          )}
          {error ? <p className="error-text">{error}</p> : null}
        </div>
      </section>

      <section className="card wide">
        <header className="card-header">
          <div>
            <h2>Registros por corregir</h2>
            <p className="card-subtitle">
              Selecciona un elemento para editar los datos críticos y marcar la incidencia como
              corregida.
            </p>
          </div>
        </header>
        <div className="card-body">
          {loading ? (
            <p className="muted-text">Cargando validaciones…</p>
          ) : validations.length === 0 ? (
            <p className="muted-text">No hay validaciones pendientes en este momento.</p>
          ) : (
            <div className="table-wrapper">
              <table className="pending-validations-table">
                <thead>
                  <tr>
                    <th scope="col">ID</th>
                    <th scope="col">Descripción</th>
                    <th scope="col">Severidad</th>
                    <th scope="col">Producto</th>
                    <th scope="col">Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {validations.map((validation) => {
                    const isSelected = validation.id === selected?.id;
                    const deviceLabel = validation.device
                      ? `${validation.device.sku} · ${validation.device.name}`
                      : "Sin dispositivo";
                    return (
                      <tr
                        key={validation.id}
                        className={isSelected ? "is-selected" : undefined}
                        onClick={() => handleSelect(validation)}
                      >
                        <td>{validation.id}</td>
                        <td>{validation.descripcion}</td>
                        <td>
                          <span
                            className={`badge ${
                              validation.severidad === "error" ? "badge-critical" : "badge-warning"
                            }`}
                          >
                            {validation.severidad}
                          </span>
                        </td>
                        <td>{deviceLabel}</td>
                        <td>{new Date(validation.fecha).toLocaleString("es-HN")}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <section className="card wide">
        <header className="card-header">
          <h2>Edición rápida</h2>
        </header>
        <div className="card-body">
          {selected?.device ? (
            <form className="validation-form" onSubmit={handleSubmit}>
              <div className="form-grid">
                <TextField
                  label="IMEI"
                  name="imei"
                  value={formState.imei}
                  onChange={handleInputChange}
                  placeholder="Ingresa el IMEI corregido"
                />
                <TextField
                  label="Número de serie"
                  name="serial"
                  value={formState.serial}
                  onChange={handleInputChange}
                  placeholder="Ingresa el número de serie"
                />
                <TextField
                  label="Marca"
                  name="marca"
                  value={formState.marca}
                  onChange={handleInputChange}
                  placeholder="Marca comercial"
                />
                <TextField
                  label="Modelo"
                  name="modelo"
                  value={formState.modelo}
                  onChange={handleInputChange}
                  placeholder="Modelo o referencia"
                />
                <TextField
                  label="Cantidad"
                  name="cantidad"
                  value={formState.cantidad}
                  onChange={handleInputChange}
                  placeholder="Actualiza el stock"
                  inputMode="numeric"
                />
                <TextField
                  label="Motivo corporativo"
                  name="reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  helperText="Se utilizará para registrar la corrección en el historial."
                />
              </div>
              <div className="form-actions">
                <Button type="submit" disabled={saving}>
                  Guardar y marcar como corregido
                </Button>
              </div>
            </form>
          ) : (
            <p className="muted-text">
              Selecciona una validación con dispositivo asociado para habilitar la edición rápida de
              campos.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}

export default CorreccionesPendientesPage;
