import { FormEvent, useMemo, useState } from "react";
import type { CatalogDevice, DeviceSearchFilters } from "../../../api";
import { searchCatalogDevices } from "../../../api";

type Props = {
  token: string;
};

const initialFilters: DeviceSearchFilters = {
  imei: "",
  serial: "",
  capacidad_gb: undefined,
  color: "",
  marca: "",
  modelo: "",
  categoria: "",
  condicion: "",
  estado: "",
  ubicacion: "",
  proveedor: "",
  fecha_ingreso_desde: "",
  fecha_ingreso_hasta: "",
};

function AdvancedSearch({ token }: Props) {
  const [filters, setFilters] = useState<DeviceSearchFilters>(initialFilters);
  const [results, setResults] = useState<CatalogDevice[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const hasFilters = useMemo(
    () =>
      Boolean(
        filters.imei ||
          filters.serial ||
          filters.color ||
          filters.marca ||
          filters.modelo ||
          filters.categoria ||
          filters.condicion ||
          filters.estado ||
          filters.ubicacion ||
          filters.proveedor ||
          typeof filters.capacidad_gb === "number" ||
          (filters.fecha_ingreso_desde ?? "") ||
          (filters.fecha_ingreso_hasta ?? "")
      ),
    [filters]
  );

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!hasFilters) {
      setError("Ingresa al menos un criterio de búsqueda");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const response = await searchCatalogDevices(token, {
        ...filters,
        capacidad_gb: typeof filters.capacidad_gb === "number" ? filters.capacidad_gb : undefined,
        categoria: filters.categoria?.trim() ? filters.categoria.trim() : undefined,
        condicion: filters.condicion?.trim() ? filters.condicion.trim() : undefined,
        estado: filters.estado?.trim() ? filters.estado.trim() : undefined,
        ubicacion: filters.ubicacion?.trim() ? filters.ubicacion.trim() : undefined,
        proveedor: filters.proveedor?.trim() ? filters.proveedor.trim() : undefined,
        fecha_ingreso_desde: filters.fecha_ingreso_desde || undefined,
        fecha_ingreso_hasta: filters.fecha_ingreso_hasta || undefined,
      });
      setResults(response);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No fue posible consultar el catálogo");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFilters(initialFilters);
    setResults([]);
    setError(null);
    setSearched(false);
  };

  return (
    <section className="card catalog-card fade-in">
      <header className="card-header">
        <h2 className="accent-title">Búsqueda avanzada de dispositivos</h2>
        <p className="card-subtitle">IMEI y serie únicos, coincidencias por marca, modelo, color y capacidad.</p>
      </header>
      <form className="catalog-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            <span>IMEI</span>
            <input
              type="text"
              value={filters.imei ?? ""}
              maxLength={18}
              placeholder="Hasta 18 dígitos"
              onChange={(event) => setFilters((state) => ({ ...state, imei: event.target.value.trim() }))}
            />
          </label>
          <label>
            <span>Serie</span>
            <input
              type="text"
              value={filters.serial ?? ""}
              maxLength={120}
              placeholder="Número de serie"
              onChange={(event) => setFilters((state) => ({ ...state, serial: event.target.value.trim() }))}
            />
          </label>
          <label>
            <span>Capacidad (GB)</span>
            <input
              type="number"
              value={typeof filters.capacidad_gb === "number" ? filters.capacidad_gb : ""}
              min={0}
              onChange={(event) =>
                setFilters((state) => ({
                  ...state,
                  capacidad_gb: event.target.value === "" ? undefined : Number(event.target.value),
                }))
              }
            />
          </label>
          <label>
            <span>Marca</span>
            <input
              type="text"
              value={filters.marca ?? ""}
              maxLength={80}
              onChange={(event) => setFilters((state) => ({ ...state, marca: event.target.value }))}
            />
          </label>
          <label>
            <span>Modelo</span>
            <input
              type="text"
              value={filters.modelo ?? ""}
              maxLength={120}
              onChange={(event) => setFilters((state) => ({ ...state, modelo: event.target.value }))}
            />
          </label>
          <label>
            <span>Color</span>
            <input
              type="text"
              value={filters.color ?? ""}
              maxLength={60}
              onChange={(event) => setFilters((state) => ({ ...state, color: event.target.value }))}
            />
          </label>
          <label>
            <span>Categoría</span>
            <input
              type="text"
              value={filters.categoria ?? ""}
              maxLength={80}
              onChange={(event) => setFilters((state) => ({ ...state, categoria: event.target.value }))}
            />
          </label>
          <label>
            <span>Condición</span>
            <input
              type="text"
              value={filters.condicion ?? ""}
              maxLength={60}
              onChange={(event) => setFilters((state) => ({ ...state, condicion: event.target.value }))}
            />
          </label>
          <label>
            <span>Estado inventario</span>
            <input
              type="text"
              value={filters.estado ?? ""}
              maxLength={40}
              onChange={(event) => setFilters((state) => ({ ...state, estado: event.target.value }))}
            />
          </label>
          <label>
            <span>Ubicación</span>
            <input
              type="text"
              value={filters.ubicacion ?? ""}
              maxLength={120}
              onChange={(event) => setFilters((state) => ({ ...state, ubicacion: event.target.value }))}
            />
          </label>
          <label>
            <span>Proveedor</span>
            <input
              type="text"
              value={filters.proveedor ?? ""}
              maxLength={120}
              onChange={(event) => setFilters((state) => ({ ...state, proveedor: event.target.value }))}
            />
          </label>
          <label>
            <span>Fecha ingreso desde</span>
            <input
              type="date"
              value={filters.fecha_ingreso_desde ?? ""}
              onChange={(event) => setFilters((state) => ({ ...state, fecha_ingreso_desde: event.target.value }))}
            />
          </label>
          <label>
            <span>Fecha ingreso hasta</span>
            <input
              type="date"
              value={filters.fecha_ingreso_hasta ?? ""}
              onChange={(event) => setFilters((state) => ({ ...state, fecha_ingreso_hasta: event.target.value }))}
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {loading ? "Buscando…" : "Buscar"}
          </button>
          <button type="button" className="ghost" onClick={handleReset} disabled={loading}>
            Limpiar
          </button>
        </div>
      </form>
      {error && <p className="error-text">{error}</p>}
      {results.length > 0 ? (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Sucursal</th>
                <th>SKU</th>
                <th>Marca</th>
                <th>Modelo</th>
                <th>Categoría</th>
                <th>Condición</th>
                <th>Color</th>
                <th>Capacidad</th>
                <th>IMEI</th>
                <th>Serie</th>
                <th>Estado</th>
                <th>Estado inventario</th>
                <th>Ubicación</th>
                <th>Ingreso</th>
              </tr>
            </thead>
            <tbody>
              {results.map((device) => (
                <tr key={`${device.id}-${device.store_id}`}>
                  <td>{device.store_name}</td>
                  <td>{device.sku}</td>
                  <td>{device.categoria ?? "—"}</td>
                  <td>{device.condicion ?? "—"}</td>
                  <td>{device.marca ?? "—"}</td>
                  <td>{device.modelo ?? "—"}</td>
                  <td>{device.color ?? "—"}</td>
                  <td>{device.capacidad_gb ?? "—"}</td>
                  <td>{device.imei ?? "—"}</td>
                  <td>{device.serial ?? "—"}</td>
                  <td>{device.estado_comercial ?? "—"}</td>
                  <td>{device.estado ?? "—"}</td>
                  <td>{device.ubicacion ?? "—"}</td>
                  <td>{device.fecha_ingreso ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : searched ? (
        <p className="muted-text">Sin resultados. Ajusta los filtros y vuelve a intentarlo.</p>
      ) : (
        <p className="muted-text">Completa los criterios para iniciar la búsqueda corporativa.</p>
      )}
    </section>
  );
}

export default AdvancedSearch;
